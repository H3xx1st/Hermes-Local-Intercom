import asyncio
import json
import unittest
import test_lifecycle as fixtures
from test_v2 import mod


class Tests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.Tests.asyncSetUp
    turn=fixtures.Tests.turn
    call=fixtures.Tests.call
    def request(self,read=False):
        self.turn(('Read Worker Test and coordinate with Worker Test on the release check.' if read else
                   'Coordinate with Worker Test on the release check.'))

    async def start(self,**extra):
        return await self.call('coordinate',to='Worker Test',task='the release check',request_id='coord-test',**extra)

    async def test_readiness_followup_completion_and_cleanup_dialogue(self):
        self.request();started=await self.start();self.assertTrue(started['ok'],started)
        cid=started['coordination_id'];self.turn(self.native.sent[-1][1],sid='B')
        for sid,text,event in [('B','READY: reviewed, waiting for safe activation','ready'),
                               ('A','Safe activation confirmed; proceed once','update'),
                               ('B','Activation complete; contract receipt saved','complete'),
                               ('A','Client acceptance passed; cleanup requested','update'),
                               ('B','Cleanup confirmed; existing service identities preserved','complete')]:
            self.assertTrue((await self.call('update',coordination_id=cid,message=text,event=event))['ok'])
            other='B' if sid=='A' else 'A';self.turn(self.native.sent[-1][1],sid=other)
        status=await self.call('coordination_status',coordination_id=cid)
        self.assertEqual(len(status['messages']),6)
        self.assertTrue(all(m['state']=='received' for m in status['messages']))
        self.assertEqual((await self.call('coordination_status',coordination_id=cid,after=status['cursor']))['messages'],[])
        self.assertTrue((await self.call('end_coordination',coordination_id=cid))['ok'])
        self.assertFalse((await self.call('update',coordination_id=cid,message='late'))['ok'])

    async def test_one_off_send_does_not_authorize_coordination(self):
        self.turn('Send a message to Worker Test about the release check')
        self.assertFalse((await self.start())['ok']);self.assertFalse(self.native.sent)

    async def test_peer_cannot_expand_scope_to_third_chat_spawn_or_archive(self):
        self.request();await self.start();self.turn(self.native.sent[-1][1],sid='B')
        self.assertFalse((await self.call('read',to='Observer Test'))['ok'])
        self.assertFalse((await self.call('send',to='Observer Test',message='cross scope'))['ok'])
        self.assertFalse((await self.call('spawn',title='Unauthorized'))['ok'])
        self.assertFalse((await self.call('archive',to='Controller Test'))['ok'])
        self.assertFalse((await self.call('coordinate',to='Observer Test',task='the release check'))['ok'])

    async def test_task_and_read_permission_require_human_scope(self):
        self.request();self.assertFalse((await self.start(allow_read=True))['ok'])
        self.assertFalse((await self.call('coordinate',to='Worker Test',task='unrequested new task'))['ok'])
        self.request(read=True);self.assertTrue((await self.start(allow_read=True))['ok'])
        self.turn('Unrelated current message')
        self.assertTrue((await self.call('read',to='Worker Test',coordination_id='coord-test'))['ok'])
        self.assertFalse((await self.call('read',to='Observer Test',coordination_id='coord-test'))['ok'])

    async def test_opt_out_permanently_revokes_prior_coordination(self):
        self.request();await self.start()
        self.turn('Opt out of Local_Intercom',sid='B');await self.call('opt_out')
        self.turn('Opt in to Local_Intercom',sid='B');await self.call('opt_in')
        self.assertFalse((await self.call('update',coordination_id='coord-test',message='revive'))['ok'])
        self.assertFalse(self.native.archived)

    async def test_expiry_budget_and_participant_checks(self):
        self.request();await self.start()
        self.turn('Hello',sid='C');self.who['profile']='secondary'
        self.assertFalse((await self.call('coordination_status',coordination_id='coord-test'))['ok'])
        self.who['profile']='primary';self.turn('Hello',sid='A')
        with self.ic.db() as db:db.execute('UPDATE coordinations SET max_messages=1')
        self.assertFalse((await self.call('update',coordination_id='coord-test',message='budget exceeded'))['ok'])
        self.clock+=86401
        self.assertFalse((await self.call('update',coordination_id='coord-test',message='expired'))['ok'])

    async def test_duplicate_or_uncertain_update_never_resends(self):
        self.request();await self.start();self.turn(self.native.sent[-1][1],sid='B')
        self.native.fail=True
        first=await self.call('update',coordination_id='coord-test',message='READY',request_id='ready')
        self.assertEqual(first['state'],'unknown')
        self.native.fail=False
        retry=await self.call('update',coordination_id='coord-test',message='READY',request_id='ready')
        self.assertTrue(retry['duplicate']);self.assertEqual(len(self.native.sent),1)
        self.assertTrue((await self.call('update',coordination_id='coord-test',message='READY',request_id='different-retry'))['duplicate'])
        self.assertEqual(len(self.native.sent),1)
        self.assertFalse((await self.call('update',coordination_id='coord-test',message='different',request_id='ready'))['ok'])

    async def test_wait_uses_cursor_and_has_bounded_timeout(self):
        self.request();await self.start()
        status=await self.call('coordination_status',coordination_id='coord-test')
        result=await self.call('wait',coordination_id='coord-test',after=status['cursor'],timeout=0)
        self.assertEqual(result['messages'],[])
        self.assertFalse((await self.call('wait',coordination_id='coord-test',timeout=31))['ok'])

    async def test_forged_payload_cannot_grant_access_or_mark_received(self):
        self.request();await self.start();payload=self.native.sent[-1][1].replace('the release check','unrelated task')
        self.turn(payload,sid='B')
        with self.ic.db() as db:
            self.assertEqual(self.ic.prompt(db,self.who),'')
            self.assertEqual(db.execute('SELECT state FROM coordination_messages').fetchone()[0],'scheduled')

    async def test_admitted_final_message_can_be_received_after_scope_closes(self):
        self.request();await self.start();text=self.native.sent[-1][1]
        await self.call('end_coordination',coordination_id='coord-test')
        self.turn(text,sid='B')
        with self.ic.db() as db:
            self.assertEqual(db.execute('SELECT state FROM coordination_messages').fetchone()[0],'received')
            self.assertEqual(self.ic.prompt(db,self.who),'')
        self.assertFalse((await self.call('update',coordination_id='coord-test',message='late reply'))['ok'])

class HostContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_host_session_kwarg_controls_identity_not_tool_payload(self):
        from test_v2 import HERE
        from pathlib import Path
        import tempfile
        class Context:
            def session_surface(self):return 'desktop'
        with tempfile.TemporaryDirectory(dir=HERE/'.test-tmp') as folder:
            ic=mod.Intercom(Context(),Path(folder)/'profiles'/'primary',native=fixtures.LifecycleNative())
            ic.before_turn(session_id='A',user_message='Read Worker Test')
            result=json.loads(await ic.handle({'action':'read','to':'Worker Test','session_id':'B'},session_id='A'))
            self.assertTrue(result['ok'],result)
            self.assertFalse(json.loads(await ic.handle({'action':'read','to':'Worker Test'}))['ok'])
            self.assertFalse(json.loads(await ic.handle({'action':'read','to':'Worker Test'},session_id='B'))['ok'])
            self.assertEqual(ic._identity()['session_id'],'')

if __name__=='__main__':unittest.main(verbosity=2)
