"""Human-scoped creation and reversible cleanup of ordinary Hermes chats."""
import hashlib
import json
from pathlib import Path
import re


class Lifecycle:
    def __init__(self,intercom):
        self.ic=intercom
        from .v2 import commands,contains,norm,SPAWN_RE
        self.commands,self.contains,self.norm,self.spawn_re=commands,contains,norm,SPAWN_RE

    def schema(self,db):
        db.execute('''CREATE TABLE IF NOT EXISTS spawns(
            id TEXT PRIMARY KEY,owner_profile TEXT,owner_sid TEXT,title TEXT,digest TEXT,
            spec TEXT,state TEXT,created REAL,child_id TEXT,cleanup INTEGER,task_id TEXT,result TEXT)''')
        db.commit()

    def instruction(self,db,who):
        text=self.ic.prompt(db,who)
        return text,[] if not text or text.startswith('REQUEST:') else self.commands(text)

    async def handle(self,db,who,me,action,args,catalog):
        self.schema(db)
        text,clauses=self.instruction(db,who)
        spawn=[c for c in clauses if re.search(self.spawn_re,c)]
        if action=='models':
            if not spawn and not any(re.match(r'^(list|show|find) (?:me )?(?:the |available |configured )*models\b',c) for c in clauses):
                raise ValueError('Ask for available models or explicitly request a new chat first.')
            return {'ok':True,**await self.ic.native.models(me)}
        if action=='spawn':
            if not spawn: raise ValueError('Creating a chat requires a direct current human request to create a new chat.')
            return await self.spawn(db,who,me,args,catalog,text)
        return await self.archive(db,who,me,args,catalog)

    def cleanup_permission(self,text):
        value=self.norm(text)
        if re.search(r'\b(do not|don t|dont|never) (archive|close)\b',value):return False
        target=r'(?:it|that (?:chat|helper)|the (?:helper|new chat|spawned chat|chat you (?:spawn|create)))'
        return bool(re.search(r'\b(?:archive|close) '+target+r'\b',value) and
                    re.search(r'\b(?:when|after|once)\b',value))

    async def spawn(self,db,who,me,args,catalog,text):
        title=args.get('title')
        if not isinstance(title,str) or not title.strip() or len(title)>150 or any(ord(c)<32 for c in title):
            raise ValueError('Give the new chat a title of 1 to 150 characters without control characters.')
        title=title.strip()
        if self.norm(title)=='bot chat':raise ValueError('Choose an ordinary chat title, not the reserved Bot Chat title.')
        if args.get('profile') and args['profile']!=who['profile']:
            raise ValueError('Spawn uses the current profile and its credentials. Cross-profile creation is not supported.')
        for key in ('model','provider','effort','project','cwd'):
            value=args.get(key)
            if value is not None and (not isinstance(value,str) or not value.strip() or not self.contains(value,text)):
                raise ValueError(f'{key} must be the value explicitly requested by the human. Omit it to inherit.')
        if args.get('effort') is not None and args['effort'] not in ('none','minimal','low','medium','high','xhigh','max','ultra'):
            raise ValueError('Unknown reasoning effort.')
        if args.get('project') and args.get('cwd'):raise ValueError('Choose project or cwd, not both.')
        task=args.get('task','')
        if not isinstance(task,str) or len(task)>8000 or (task and not self.contains(task,text)):
            raise ValueError('task must be a verbatim excerpt of the current human task, at most 8000 characters.')
        cleanup=args.get('archive_when_done',False)
        if type(cleanup) is not bool or (cleanup and not self.cleanup_permission(text)):
            raise ValueError('archive_when_done requires explicit human permission to archive this helper after completion.')
        requested={k:args[k] for k in ('model','provider','effort','project','cwd') if k in args}
        requested.update(title=title,task=task,archive_when_done=cleanup)
        digest=hashlib.sha256(json.dumps([who['profile'],who['session_id'],requested],sort_keys=True).encode()).hexdigest()
        rid=self.ic.rid(args) if args.get('request_id') else 'spawn-'+digest[:40]
        row=db.execute('SELECT * FROM spawns WHERE id=?',(rid,)).fetchone()
        if row is None:
            row=db.execute('SELECT * FROM spawns WHERE owner_profile=? AND owner_sid=? AND digest=?',
                           (who['profile'],who['session_id'],digest)).fetchone()
            if row:rid=row['id']
        task_id=(rid+'-task' if len(rid)<=91 else 'task-'+hashlib.sha256(rid.encode()).hexdigest()) if task else None
        if row and (row['digest']!=digest or row['owner_profile']!=who['profile'] or row['owner_sid']!=who['session_id']):
            raise ValueError('request_id belongs to a different creation request.')
        if row and row['result']:
            return {**json.loads(row['result']),'duplicate':True}
        if not row:
            # Never use title-keyed session.create: Hermes may resume a pre-existing title.
            if any(c['profile']==who['profile'] and self.norm(c['title'])==self.norm(title) for c in catalog):
                raise ValueError('That title is unavailable. Choose a new title; existing conversations are never reused.')
            if not self.ic.native.title_available(who['profile'],title):
                raise ValueError('That title is unavailable. Choose a new title; existing conversations are never reused.')
            count=db.execute('SELECT count(*) FROM spawns WHERE owner_profile=? AND owner_sid=? AND created>?',
                             (who['profile'],who['session_id'],self.ic.clock()-60)).fetchone()[0]
            if count>=3:raise ValueError('Limit: three new chats per minute.')
            spec=await self.ic.native.spawn_spec(me,requested)
            db.execute('INSERT INTO spawns VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (rid,who['profile'],who['session_id'],title,digest,json.dumps(spec),'creating',self.ic.clock(),None,int(cleanup),task_id,None))
            db.commit()
        else:spec=json.loads(row['spec'])
        def created(sid):
            db.execute('UPDATE spawns SET child_id=? WHERE id=?',(sid,rid));db.commit()
        try:
            child=await self.ic.native.spawn(me,spec,'Local_Intercom-'+rid,created)
        except Exception:
            db.execute("UPDATE spawns SET state='unknown' WHERE id=?",(rid,));db.commit()
            raise ValueError('Creation outcome uncertain. Retry the SAME request_id and arguments; do not create a replacement.') from None
        db.execute("UPDATE spawns SET state='created',child_id=? WHERE id=?",(child['id'],rid));db.commit()
        result={'ok':True,'id':rid,'chat':self.ic.public(child),'model':child.get('model'),
                'effort':child.get('effort'),'effective_effort':child.get('effective_effort'),
                'archive_when_done':cleanup,'state':'created'}
        if task:
            task_result=await self.ic.send(db,who,me,child,{'message':task,'request_id':task_id})
            result['task']=task_result
        result['note']='New ordinary chat; no existing history copied. Archive only after using its completed result and only if cleanup permission was granted.'
        db.execute('UPDATE spawns SET result=? WHERE id=?',(json.dumps(result),rid))
        return result

    async def archive(self,db,who,me,args,catalog):
        target_name=args.get('to')
        if not isinstance(target_name,str) or not target_name.strip():raise ValueError('Name the chat to archive using to.')
        owned=db.execute('SELECT * FROM spawns WHERE owner_profile=? AND owner_sid=? AND child_id IS NOT NULL',
                         (who['profile'],who['session_id'])).fetchall()
        row=next((r for r in owned if target_name in (r['child_id'],who['profile']+'::'+r['child_id']) or self.norm(target_name)==self.norm(r['title'])),None)
        target=next((c for c in catalog if row and c['profile']==who['profile'] and row['child_id'] in set(c.get('aliases',[]))|{c['id']}),None)
        if target is None and row:
            target={'id':row['child_id'],'title':row['title'],'profile':row['owner_profile'],'aliases':[row['child_id']]}
        if target is None:
            self.ic.authorize(db,who,'archive')
            authorized=[]
            for candidate in catalog:
                try:self.ic.authorize(db,who,'archive',candidate,args.get('to'));authorized.append(candidate)
                except ValueError:pass
            target=self.ic.resolve(db,authorized,target_name,args.get('profile'))
        if (target['profile'],target['id'])==(me['profile'],me['id']):raise ValueError('Use Hermes itself to archive the current chat.')
        if self.ic.blocked(db,target):raise ValueError('Chat unavailable for Local_Intercom.')
        explicit=False
        try:self.ic.authorize(db,who,'archive',target,args.get('to'));explicit=True
        except ValueError:pass
        if not explicit:
            if not row or not row['cleanup'] or not row['task_id']:
                raise ValueError('Archiving requires a current named human request or the creator\'s recorded completed-helper cleanup grant.')
            request=db.execute('SELECT * FROM requests WHERE id=?',(row['task_id'],)).fetchone()
            if not request or request['state']!='replied' or request['reply_state']!='received':
                raise ValueError('The helper result has not yet been received by its creator.')
        if row and row['state']=='archived':return {'ok':True,'state':'archived','duplicate':True,'chat':self.ic.public(target)}
        # Order opt-out against archival, like read/admission. The native mutation is revision/generation fenced.
        if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
        if self.ic.blocked(db,me) or self.ic.blocked(db,target):raise ValueError('Chat unavailable for Local_Intercom.')
        result=await self.ic.native.archive(target,'Local_Intercom-archive-'+hashlib.sha256((who['profile']+who['session_id']+target['id']).encode()).hexdigest()[:40])
        if row:db.execute("UPDATE spawns SET state='archived' WHERE id=?",(row['id'],))
        return {'ok':True,'state':'archived','chat':self.ic.public(target),'history_preserved':True,**result}
