import unittest
from gateway_compat import CheckedClient

class Client:
    def __init__(self,result):self.result=result;self.calls=[]
    async def rpc(self,method,**params):self.calls.append((method,params));return self.result

class Tests(unittest.IsolatedAsyncioTestCase):
    async def test_unexpected_rpc_is_refused_before_native_call(self):
        raw=Client({});client=CheckedClient(raw)
        with self.assertRaises(ValueError):await client.rpc('session.delete',session_id='anything')
        self.assertFalse(raw.calls)
    async def test_changed_create_contract_is_reported_as_uncertain(self):
        client=CheckedClient(Client({'unexpected':'shape'}))
        with self.assertRaisesRegex(ValueError,'uncertain'):await client.rpc('session.create',request_id='keep-stable')
    async def test_stable_identity_and_result_are_preserved(self):
        result={'admission_id':'a','status':'queued'};raw=Client(result)
        self.assertEqual(await CheckedClient(raw).rpc('prompt.submit',session_id='s',submission_id='stable',text='hello'),result)
        self.assertEqual(raw.calls[0][1]['submission_id'],'stable')
