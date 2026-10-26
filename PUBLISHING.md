# Publishing Local_Intercom

Hermes supports standalone agent plugins used inside Desktop; a renderer plugin.js
is only needed for custom Desktop UI. This package currently adds an agent tool
and a pre-LLM hook, with no additional service or listener.

## Official route

1. Publish the reviewed candidate to H3xx1st/hermes-local-intercom with plugin.yaml, __init__.py, runtime sources,
   documentation, license and truthful compatibility metadata.
2. Run `hermes plugins validate <plugin-directory> --install-deps` at the exact
   proposed commit. The local check without dependency installation currently passes;
   the source uses packages already present in Hermes and declares no added dependencies.
3. Submit one `plugin-catalog/<name>.yaml` entry to NousResearch/hermes-agent,
   pinning the plugin repository to a full 40-character commit SHA and quoting version.
4. Describe the plugin's surfaces and disclosures. A Hermes maintainer reviews the
   pinned source and CI must pass. Future pin changes require another reviewed PR.

These are Hermes's [catalog submission requirements](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission).
Direct Git installation is also supported before catalog admission; see
[installing plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins).

## Publication review still needed

- Owner/author H3xx1st and MIT have been explicitly selected. Standalone source
  publication is authorized at H3xx1st/hermes-local-intercom, with compatibility
  warnings visible. Catalog admission remains a separate step.
- `requires_hermes` is >=0.22.2, the tested live gateway version. Keep the catalog
  compatibility floor aligned with the manifest.
- Three undocumented native client imports remain isolated in gateway_compat.py.
  Private identity and project-list imports were removed. The remaining imports
  produce validator warnings and can change across Hermes releases. Passing validation alone does not
  establish maintainer acceptance. Hermes recommends asking for a supported seam
  where the documented plugin surface is insufficient.
- The API request was submitted as [NousResearch/hermes-agent#145227](https://github.com/NousResearch/hermes-agent/issues/145227)
  on 27 October 2026; UPSTREAM_API_REQUEST.md records its scope. No maintainer
  approval or supported replacement is claimed while the request is pending.
- Complete the exact-file privacy audit and package hash checks in RELEASE_CHECKLIST.md.
- Ship only reviewed runtime sources and tests/docs. The development folder also
  retains private chat IDs, prompts, local paths and evidence, which are ignored by
  Git and must stay out of a public release.
- Validate a clean install and the target Hermes release on supported platforms;
  the current live test scope is local Windows Desktop.

## Required disclosures

This plugin reads ordinary-session metadata from local profile state databases and
project metadata from project databases. Model choice also reads profile configuration
to project model-alias metadata. It stores privacy, request and helper ownership records
in plugin-owned shared storage under the Hermes root. Read requests retrieve bounded
recent user/assistant text through the native gateway. Messages and explicit helper
tasks cause the target chat to use its existing model/provider; that provider may be
remote and may incur normal usage costs. The plugin does not manage OAuth tokens.

Native authenticated gateway clients create ordinary chats, submit prompts and apply
reversible metadata archives. There is no added listener, external MCP server, runtime
shell child, telemetry or self-updater. Developer deployment/test scripts are separate
from the runtime. Opt-out is enforced for this plugin's operations; it is not OS-level
encryption or a restriction on other plugins/tools with independent filesystem access.

Hermes documents public plugin surfaces, persistent storage and capability declaration
in [Build a Hermes Plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins).
Catalog rules require disclosure of reads outside plugin storage and reject runtime
core overrides and credential-store workarounds.

The original hermes-intercom reference is credited in THIRD_PARTY_NOTICES.md with
its MIT notice. The official catalog also has a one-listing-per-lineage rule: a
fork must have a material platform/transport difference or satisfy the documented
upstream contribution conditions. Disclose the native ordinary-Desktop gateway
transport and permission/lifecycle differences; maintainer acceptance is not assumed.
