"""Small, explicit compatibility boundary for Hermes's native local gateway client.

These three imports remain internal Hermes APIs. Keep them visible to admission
lint; never dynamically import them to hide a warning. No fallback starts a runtime,
reads an OAuth file, copies tokens or writes a Hermes conversation database.
"""
from contextlib import asynccontextmanager


class CheckedClient:
    METHODS={'session.info','session.resume','session.create','session.mutate','prompt.submit','model.options'}
    REQUIRED={'session.info':{'model','cwd'},'session.resume':{'session_id','revision','execution_generation','messages'},
              'session.create':{'session_id','revision','execution_generation'},'session.mutate':{'operation','revision'},
              'prompt.submit':{'admission_id','status'},'model.options':{'providers'}}

    def __init__(self,client):self.client=client

    async def rpc(self,method,**params):
        if method not in self.METHODS:raise ValueError('Unsupported Local_Intercom gateway operation.')
        result=await self.client.rpc(method,**params)
        if not isinstance(result,dict) or not self.REQUIRED[method].issubset(result):
            raise ValueError('Hermes gateway contract changed. Operation outcome may be uncertain; keep the same retry ID.')
        return result


@asynccontextmanager
async def existing_client(home):
    from hermes_constants import set_hermes_home_override,reset_hermes_home_override
    try:
        from hermes_cli.gateway_runtime import discover_gateway_endpoint,attachable
        from hermes_cli.gateway_client import connect_gateway
    except ImportError:
        raise ValueError('This Hermes build lacks the required native client. Local_Intercom did not start a service.') from None
    token=set_hermes_home_override(home)
    try:
        found=discover_gateway_endpoint(home)
        if not attachable(found):raise ValueError('Target gateway offline or unavailable. No service was started.')
        async with connect_gateway(endpoint=found.endpoint) as client:
            description=await client.rpc('runtime.describe')
            creation=description.get('session_create',{}) if isinstance(description,dict) else {}
            if 'gui' not in creation.get('sources',[]) or not {'cwd','model','provider','reasoning'}.issubset(creation.get('parameters',[])):
                raise ValueError('Unsupported Hermes session gateway contract; no chat operation was attempted.')
            yield CheckedClient(client)
    finally:reset_hermes_home_override(token)
