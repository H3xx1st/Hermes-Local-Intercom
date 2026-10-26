"""Durable, bounded human-authorized dialogue between exactly two ordinary chats."""
import asyncio
import hashlib
import json


class Coordination:
    ACTIONS={'coordinate','update','coordination_status','wait','end_coordination'}

    def __init__(self,intercom):
        self.ic=intercom
        from .v2 import commands,contains
        self.commands,self.contains=commands,contains

    @staticmethod
    def schema(db):
        db.executescript('''CREATE TABLE IF NOT EXISTS coordinations(
            id TEXT PRIMARY KEY,owner_profile TEXT,owner_sid TEXT,peer_profile TEXT,peer_sid TEXT,
            task TEXT,state TEXT,created REAL,expires REAL,max_messages INTEGER,allow_read INTEGER DEFAULT 0);
          CREATE TABLE IF NOT EXISTS coordination_messages(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE,coordination_id TEXT,
            sender_profile TEXT,sender_sid TEXT,recipient_profile TEXT,recipient_sid TEXT,
            message TEXT,event TEXT,state TEXT,created REAL,admission_id TEXT);''')

    def participant(self,row,me):
        ids=set(me.get('aliases',[]))|{me['id']}
        for side in ('owner','peer'):
            if row[side+'_profile']==me['profile'] and row[side+'_sid'] in ids:return side
        raise ValueError('Coordination is not available to this chat.')

    def get(self,db,me,cid,active=True):
        if not isinstance(cid,str) or not cid:raise ValueError('coordination_id is required.')
        row=db.execute('SELECT * FROM coordinations WHERE id=?',(cid,)).fetchone()
        if not row:raise ValueError('Coordination is not available to this chat.')
        side=self.participant(row,me)
        if active and (row['state']!='active' or row['expires']<=self.ic.clock()):
            raise ValueError('Coordination is closed or expired; a new human request is required.')
        return row,side

    def peer(self,row,side,catalog):
        other='peer' if side=='owner' else 'owner'
        target=next((c for c in catalog if c['profile']==row[other+'_profile'] and
                     row[other+'_sid'] in set(c.get('aliases',[]))|{c['id']}),None)
        if target is None:raise ValueError('Coordination peer is unavailable.')
        return target

    def privacy(self,db,me,row,side,catalog):
        target=self.peer(row,side,catalog)
        if self.ic.blocked(db,me) or self.ic.blocked(db,target):raise ValueError('Chat unavailable for Local_Intercom.')
        return target

    async def handle(self,db,who,me,action,args,catalog):
        self.schema(db)
        if action=='coordinate':return await self.start(db,who,me,args,catalog)
        row,side=self.get(db,me,args.get('coordination_id'),active=action in ('update','wait'))
        target=self.privacy(db,me,row,side,catalog)
        if action=='update':return await self.emit(db,me,target,row,args)
        if action=='end_coordination':
            db.execute("UPDATE coordinations SET state='closed' WHERE id=?",(row['id'],))
            return {'ok':True,'coordination_id':row['id'],'state':'closed','note':'Only this task dialogue was closed; no chat was archived.'}
        if action=='wait':
            timeout=args.get('timeout',20)
            if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not 0<=timeout<=30:
                raise ValueError('wait timeout must be 0 to 30 seconds.')
            loop=asyncio.get_running_loop();deadline=loop.time()+timeout
            while True:
                current,_=self.get(db,me,row['id'],active=False)
                self.privacy(db,me,current,side,self.ic.native.catalog())
                result=self.status(db,me,current,args)
                if result['messages'] or current['state']!='active' or current['expires']<=self.ic.clock() or loop.time()>=deadline:return result
                # Tool-scoped bounded wait, never a background service/listener or a held write lock.
                db.commit()
                await asyncio.sleep(min(0.5,max(0,deadline-loop.time())))
        return self.status(db,me,row,args)

    async def start(self,db,who,me,args,catalog):
        text=self.ic.prompt(db,who)
        clauses=[] if text.startswith(('REQUEST:','CHANNEL:')) else self.commands(text)
        direct=[c for c in clauses if c.startswith(('coordinate ','liaise ','liase ','see and liaise ','read and liaise '))]
        if not direct:raise ValueError('Ongoing coordination requires a direct human request to coordinate with a named chat on a task.')
        allowed=[c for c in catalog if any(self.ic.named(clause,c,args.get('to')) for clause in direct)]
        target=self.ic.resolve(db,allowed,args.get('to'),args.get('profile'))
        if (target['profile'],target['id'])==(me['profile'],me['id']):raise ValueError('Choose another chat.')
        task=args.get('task')
        if not isinstance(task,str) or not task.strip() or len(task)>2000 or not self.contains(task,text):
            raise ValueError('task must be a verbatim excerpt of the human coordination task, at most 2000 characters.')
        if self.ic.blocked(db,target):raise ValueError('Chat unavailable for Local_Intercom.')
        allow_read=args.get('allow_read',False)
        if type(allow_read) is not bool:raise ValueError('allow_read must be a boolean.')
        if allow_read:self.ic.authorize(db,who,'read',target,args.get('to'))
        cid=self.ic.rid(args) if args.get('request_id') else 'coord-'+hashlib.sha256(json.dumps([me['profile'],me['id'],target['profile'],target['id'],task]).encode()).hexdigest()[:40]
        existing=db.execute('SELECT * FROM coordinations WHERE id=?',(cid,)).fetchone()
        if existing:
            if (existing['owner_profile'],existing['owner_sid'],existing['peer_profile'],existing['peer_sid'],existing['task'],existing['allow_read'])!=(me['profile'],me['id'],target['profile'],target['id'],task,int(allow_read)):
                raise ValueError('request_id belongs to different coordination content or participants.')
            self.get(db,me,cid)
            return {'ok':True,'coordination_id':cid,'state':existing['state'],'duplicate':True}
        target=await self.ic.native.prepare(target)
        if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
        if self.ic.blocked(db,me) or self.ic.blocked(db,target):raise ValueError('Chat unavailable for Local_Intercom.')
        db.execute('INSERT INTO coordinations VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (cid,me['profile'],me['id'],target['profile'],target['id'],task,'active',self.ic.clock(),self.ic.clock()+86400,32,int(allow_read)))
        db.commit()
        row=db.execute('SELECT * FROM coordinations WHERE id=?',(cid,)).fetchone()
        initial=await self.emit(db,me,target,row,{'message':task,'event':'request','request_id':'start-'+hashlib.sha256(cid.encode()).hexdigest()[:40]})
        return {'ok':initial['ok'],'coordination_id':cid,'state':'active','task':task,'peer':self.ic.public(target),
                'expires':row['expires'],'max_messages':32,'allow_read':allow_read,'initial':initial,
                'note':'Explicit task-scoped dialogue, only these two chats. Send useful updates, not acknowledgements. End when complete.'}

    async def emit(self,db,me,target,row,args):
        body=self.ic.text(args);event=args.get('event','update')
        if event not in ('request','update','ready','complete'):raise ValueError('Use request, update, ready or complete for event.')
        digest=hashlib.sha256(json.dumps([row['id'],me['profile'],me['id'],body,event]).encode()).hexdigest()
        mid=self.ic.rid(args) if args.get('request_id') else 'msg-'+digest[:40]
        if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
        current,side=self.get(db,me,row['id'])
        self.privacy(db,me,current,side,self.ic.native.catalog())
        prior=db.execute('SELECT * FROM coordination_messages WHERE id=?',(mid,)).fetchone()
        if prior:
            if (prior['coordination_id'],prior['sender_profile'],prior['sender_sid'],prior['message'],prior['event'])!=(row['id'],me['profile'],me['id'],body,event):
                raise ValueError('request_id belongs to another coordination message.')
            return {'ok':prior['state'] in ('scheduled','received'),'id':mid,'state':prior['state'],'duplicate':True}
        prior=db.execute('SELECT * FROM coordination_messages WHERE coordination_id=? AND sender_profile=? AND sender_sid=? AND message=? AND event=? ORDER BY seq LIMIT 1',
                         (row['id'],me['profile'],me['id'],body,event)).fetchone()
        if prior:return {'ok':prior['state'] in ('scheduled','received'),'id':prior['id'],'state':prior['state'],'duplicate':True}
        count=db.execute('SELECT count(*) FROM coordination_messages WHERE coordination_id=?',(row['id'],)).fetchone()[0]
        if count>=current['max_messages']:raise ValueError('Coordination message budget exhausted; a new human request is required.')
        rate=db.execute('SELECT count(*) FROM coordination_messages WHERE sender_profile=? AND sender_sid=? AND created>?',
                        (me['profile'],me['id'],self.ic.clock()-60)).fetchone()[0]
        if rate>=6:raise ValueError('Limit: six coordination messages per chat per minute.')
        db.execute('INSERT INTO coordination_messages(id,coordination_id,sender_profile,sender_sid,recipient_profile,recipient_sid,message,event,state,created) VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (mid,row['id'],me['profile'],me['id'],target['profile'],target['id'],body,event,'dispatching',self.ic.clock()))
        db.commit()
        payload='[Local_Intercom coordination]\n'+json.dumps({'coordination_id':row['id'],'message_id':mid,
            'from_chat':me['title'],'task':row['task'],'event':event,'message':body},ensure_ascii=False)+(
            '\nThe human authorized coordination with this peer ONLY for the recorded task. Use update with coordination_id '
            'for a useful readiness/result/follow-up. Do not send acknowledgements or echo messages. Do not use one-off reply. '
            'No third-chat access, spawning, archival or approvals are granted. End coordination when the task and cleanup are complete.')
        state,admission=await self.ic.deliver(db,me,target,payload,'Local_Intercom-coord-'+hashlib.sha256(mid.encode()).hexdigest())
        db.execute('UPDATE coordination_messages SET state=?,admission_id=? WHERE id=?',(state,admission,mid))
        return {'ok':state=='scheduled','coordination_id':row['id'],'id':mid,'state':state,
                'note':'Scheduling is not delivery. End this turn quietly; useful peer updates arrive automatically.'}

    def status(self,db,me,row,args):
        after=args.get('after',0)
        if type(after) is not int or after<0:raise ValueError('after must be a nonnegative cursor.')
        messages=db.execute('SELECT seq,id,sender_profile,sender_sid,event,message,state FROM coordination_messages WHERE coordination_id=? AND seq>? ORDER BY seq LIMIT 20',(row['id'],after)).fetchall()
        cursor=messages[-1]['seq'] if messages else after
        return {'ok':True,'coordination_id':row['id'],'state':row['state'] if row['expires']>self.ic.clock() else 'expired',
                'task':row['task'],'messages':[dict(m) for m in messages],'cursor':cursor,'expires':row['expires']}

    def receive(self,db,me,text):
        self.schema(db)
        try:payload=json.JSONDecoder().raw_decode(text.split('\n',1)[1])[0]
        except (ValueError,IndexError):return ''
        message=db.execute('SELECT * FROM coordination_messages WHERE id=?',(payload.get('message_id'),)).fetchone()
        if not message or message['coordination_id']!=payload.get('coordination_id') or message['message']!=payload.get('message'):return ''
        if message['recipient_profile']!=me['profile'] or message['recipient_sid'] not in set(me.get('aliases',[]))|{me['id']}:return ''
        try:
            row,side=self.get(db,me,message['coordination_id'],active=False)
            if payload.get('task')!=row['task'] or payload.get('event')!=message['event']:return ''
            self.privacy(db,me,row,side,self.ic.native.catalog())
        except ValueError:return ''
        db.execute("UPDATE coordination_messages SET state='received' WHERE id=?",(message['id'],))
        return 'CHANNEL:'+row['id'] if row['state']=='active' and row['expires']>self.ic.clock() else ''

    def authorize_read(self,db,me,target,cid):
        self.schema(db);row,side=self.get(db,me,cid)
        peer=self.privacy(db,me,row,side,self.ic.native.catalog())
        if not row['allow_read'] or side!='owner' or (peer['profile'],peer['id'])!=(target['profile'],target['id']):
            raise ValueError('This coordination does not grant this transcript read.')

    @staticmethod
    def revoke_for(db,profile,ids):
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='coordinations'").fetchone():
            for sid in ids:
                db.execute("UPDATE coordinations SET state='closed' WHERE (owner_profile=? AND owner_sid=?) OR (peer_profile=? AND peer_sid=?)",(profile,sid,profile,sid))
