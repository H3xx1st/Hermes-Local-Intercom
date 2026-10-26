"""Existing Hermes session gateway clients. Never starts a service or listener."""
from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3

class NativeSessions:
    def __init__(self, root): self.root = Path(root)

    def homes(self):
        result = {'default': self.root}
        profiles = self.root / 'profiles'
        if profiles.is_dir():
            result.update({p.name:p for p in profiles.iterdir() if p.is_dir()
                           and not p.name.startswith('.') and (p/'state.db').is_file()})
        return result

    def catalog(self):
        result=[]
        for profile,home in self.homes().items():
            path=home/'state.db'; db=None
            if not path.is_file(): continue
            try:
                db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2); db.row_factory=sqlite3.Row
                columns={r[1] for r in db.execute('PRAGMA table_info(sessions)')}
                fields=[k for k in ('id','title','source','cwd','chat_id','parent_session_id','end_reason','started_at') if k in columns]
                predicates=["source IN ('gui','desktop','local','cli','tui')"]
                predicates += [f'COALESCE({col},0)=0' for col in ('hidden','archived') if col in columns]
                rows=[dict(r) for r in db.execute('SELECT '+','.join(fields)+' FROM sessions WHERE '+' AND '.join(predicates))]
                parents={r.get('parent_session_id') for r in rows}; by_id={r['id']:r for r in rows}
                for row in rows:
                    if row['id'] in parents and row.get('end_reason')=='compression': continue
                    aliases={row['id']}; owner=row.get('chat_id')
                    if owner: aliases.add(owner)
                    parent=row.get('parent_session_id'); seen=set()
                    while parent and parent not in seen:
                        seen.add(parent); ancestor=by_id.get(parent)
                        if not ancestor or ancestor.get('end_reason')!='compression': break
                        aliases.add(parent)
                        if ancestor.get('chat_id'): aliases.add(ancestor['chat_id'])
                        parent=ancestor.get('parent_session_id')
                    result.append({'id':owner or row['id'],'stored_id':row['id'],'title':row.get('title') or '(untitled)',
                                   'profile':profile,'cwd':row.get('cwd') or '', 'aliases':sorted(aliases),
                                   'started_at':row.get('started_at') or 0})
            except (sqlite3.Error,OSError): continue
            finally:
                if db: db.close()
        return list({(c['profile'],c['id']):c for c in sorted(result,key=lambda c:c['started_at'])}.values())

    @asynccontextmanager
    async def client(self, profile):
        from .gateway_compat import existing_client
        home=self.homes().get(profile)
        if home is None: raise ValueError('Target profile unavailable.')
        async with existing_client(home) as client:yield client

    async def read(self,target,limit=12):
        async with self.client(target['profile']) as client:
            snap=await client.rpc('session.resume',session_id=target['id'])
            messages=[{'role':r['role'],'text':r['content'][:2000]} for r in snap.get('messages') or []
                      if r.get('role') in ('user','assistant') and isinstance(r.get('content'),str) and r['content']]
            return {'messages':messages[-limit:],'running':bool(snap.get('running'))}

    async def prepare(self,target):
        """Resolve legacy/compressed IDs through the owner before recording a request's recipient."""
        async with self.client(target['profile']) as client:
            snap=await client.rpc('session.resume',session_id=target['id'])
            return {**target,'id':snap['session_id'],
                    'aliases':sorted(set(target.get('aliases',[]))|{target['id'],snap['session_id']})}

    async def deliver(self,target,text,submission_id,before_submit):
        async with self.client(target['profile']) as client:
            snap=await client.rpc('session.resume',session_id=target['id'])
            before_submit(snap['session_id'])
            return await client.rpc('prompt.submit',session_id=snap['session_id'],text=text,submission_id=submission_id)

    async def settings(self,me):
        async with self.client(me['profile']) as client:
            info=await client.rpc('session.info',session_id=me['id'])
            return {k:info.get(k) for k in ('model','provider','cwd','project','reasoning_effort','reasoning_effort_wire')}

    def title_available(self,profile,title):
        # Include hidden/archived history so a duplicate title cannot orphan a newly created chat.
        path=self.homes()[profile]/'state.db'
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            return db.execute('SELECT 1 FROM sessions WHERE title=? COLLATE NOCASE LIMIT 1',(title,)).fetchone() is None

    async def models(self,me):
        import yaml
        async with self.client(me['profile']) as client:
            data=await client.rpc('model.options',session_id=me['id'],explicit_only=True,include_unconfigured=False,refresh=False)
            # Return only picker identifiers/capabilities. Never project credentials/endpoints/usage.
            providers=[{k:p[k] for k in ('slug','name','models','model_capabilities') if k in p} for p in data.get('providers',[])]
            config=yaml.safe_load((self.homes()[me['profile']]/'config.yaml').read_text(encoding='utf-8')) or {}
            aliases=[]
            for name,value in (config.get('model_aliases') or {}).items():
                if isinstance(value,str):aliases.append({'alias':name,'model':value})
                elif isinstance(value,dict):aliases.append({'alias':name,**{k:value[k] for k in ('model','provider') if k in value}})
            return {'providers':providers,'aliases':aliases,'current_model':data.get('model'),'current_provider':data.get('provider'),
                    'effort_levels':['none','minimal','low','medium','high','xhigh','max','ultra'],
                    'note':'Hermes may clamp effort to model support; spawn reports configured and effective effort.'}

    def project_cwd(self,profile,name):
        path=self.homes()[profile]/'projects.db'
        if not path.is_file():raise ValueError('No project catalog in this profile.')
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            rows=db.execute('SELECT id,slug,name,primary_path FROM projects WHERE COALESCE(archived,0)=0').fetchall()
            matches=[p for p in rows if name.casefold() in (p['id'].casefold(),p['slug'].casefold(),p['name'].casefold())]
        if len(matches)!=1 or not matches[0]['primary_path']:raise ValueError('Name one existing project with a primary folder.')
        return matches[0]['primary_path']

    async def spawn_spec(self,me,requested):
        settings=await self.settings(me)
        cwd=requested.get('cwd') or (self.project_cwd(me['profile'],requested['project']) if requested.get('project') else settings.get('cwd'))
        if not cwd or not Path(cwd).is_absolute() or not Path(cwd).is_dir():raise ValueError('New chat needs an existing absolute project folder.')
        model=requested.get('model') or settings.get('model');provider=requested.get('provider')
        if not model:raise ValueError('Name a configured model or alias.')
        choices=await self.models(me)
        alias=next((a for a in choices['aliases'] if a['alias']==model),None)
        if alias:
            # The native owner resolves the alias, including its profile-bound credentials.
            pass
        else:
            if ':' in model and not provider:
                prefix,rest=model.split(':',1)
                if any(p['slug']==prefix for p in choices['providers']):provider,model=prefix,rest
            matches=[p['slug'] for p in choices['providers'] if model in p.get('models',[]) and (not provider or p['slug']==provider)]
            current_provider=choices.get('current_provider') or settings.get('provider')
            if not requested.get('model') and not provider:provider=current_provider
            elif not provider and current_provider in matches:provider=current_provider
            elif not provider and len(matches)==1:provider=matches[0]
            if not provider or (not matches and (model,provider)!=(settings.get('model'),settings.get('provider'))):
                raise ValueError('Choose an available model and an unambiguous configured provider from models.')
        effort=requested.get('effort') or settings.get('reasoning_effort') or 'medium'
        spec={'title':requested['title'],'cwd':str(cwd),'model':model,'reasoning':effort}
        if provider:spec['provider']=provider
        return spec

    async def spawn(self,me,spec,request_id,created):
        async with self.client(me['profile']) as client:
            # No title on create: title-keyed create can resume an existing conversation.
            snap=await client.rpc('session.create',request_id=request_id,source='gui',
                                  **{k:v for k,v in spec.items() if k!='title'})
            sid=snap['session_id'];created(sid)
            stored=next((c for c in self.catalog() if c['profile']==me['profile'] and sid in set(c.get('aliases',[]))|{c['id']}),None)
            if stored is None or stored['title']!=spec['title']:
                await client.rpc('session.mutate',session_id=sid,operation='rename',payload={'title':spec['title']},
                                 request_id=request_id+'-title',expected_revision=snap['revision'])
            info=await client.rpc('session.info',session_id=sid)
            return {'id':sid,'aliases':[sid],'title':spec['title'],'profile':me['profile'],'cwd':info.get('cwd'),
                    'model':info.get('model'),'effort':info.get('reasoning_effort'),'effective_effort':info.get('reasoning_effort_wire')}

    async def archive(self,target,request_id):
        async with self.client(target['profile']) as client:
            snap=await client.rpc('session.resume',session_id=target['id'])
            if snap.get('running') or any(p.get('status') in ('queued','started','unknown') for p in snap.get('prompts',[])):
                raise ValueError('Chat is busy; no archive or interruption performed. Retry after it is idle.')
            path=self.homes()[target['profile']]/'state.db'
            with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
                row=db.execute('SELECT archived FROM sessions WHERE id=?',(snap.get('stored_session_id') or snap['session_id'],)).fetchone()
                if row and row[0]:return {'native_status':'already_archived'}
            # Metadata archive preserves transcript. Generation/revision fence protects against stale work.
            result=await client.rpc('session.mutate',session_id=snap['session_id'],operation='archive',payload={'archived':True},
                request_id=request_id,expected_revision=snap['revision'],expected_generation=snap['execution_generation'])
            if result.get('operation')!='archive':
                raise ValueError('Native archive did not confirm success; no deletion was requested.')
            with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
                row=db.execute('SELECT archived FROM sessions WHERE id=?',(snap.get('stored_session_id') or snap['session_id'],)).fetchone()
            if not row or not row[0]:raise ValueError('Archive flag was not confirmed. No deletion was requested.')
            return {'native_status':'archived'}
