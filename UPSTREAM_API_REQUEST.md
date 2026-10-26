# Submitted request: supported ordinary-chat client API for Python plugins

Submitted on 27 October 2026 as
[NousResearch/hermes-agent#145227](https://github.com/NousResearch/hermes-agent/issues/145227).
Maintainer guidance is pending. This document summarizes the request; no approval
or supported replacement API is claimed.

Local_Intercom is an in-process Python tool plugin for explicit human-authorized
coordination between ordinary Desktop chats. It uses registered tools, the
pre_llm_call hook, host session_id kwargs, ctx.session_surface and plugin-owned
storage. It starts no daemon, listener, shell child or external MCP server.

The remaining compatibility boundary imports:

- hermes_cli.gateway_runtime.discover_gateway_endpoint
- hermes_cli.gateway_runtime.attachable
- hermes_cli.gateway_client.connect_gateway

We keep these imports explicit so catalog lint reports them. Contract checks
refuse an unsupported gateway before attempting chat operations; we never call
ensure_gateway_runtime or work around failures by reading token files or
writing Hermes conversation databases directly.

Could Hermes expose a supported profile-scoped Python facade (for example,
ctx.sessions) covering existing-runtime discovery, session list/info/resume,
prompt admission/receipt, ordinary GUI chat creation, reversible archive,
and configured model options? It should preserve native credentials, approvals,
profile ownership, stable request IDs and revision/generation fences and offer
an explicit no-start option for unavailable profiles.

The Desktop SDK already documents host.request/host.requestProfile. The missing
seam here is the equivalent supported client for an agent-side Python plugin.
We would prefer that seam to depending on internal gateway client imports.

Can maintainers confirm whether the current read-only metadata plus native RPC
approach is acceptable for an experimental catalog entry, and which public
surface they recommend? Catalog acceptance remains pending that review.
