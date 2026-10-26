# Hermes Local Intercom 0.4.0 publication candidate

Prepared for H3xx1st/Hermes-Local-Intercom under MIT. The user authorized standalone
GitHub publication. [Hermes API request #145227](https://github.com/NousResearch/hermes-agent/issues/145227)
has been submitted; catalog admission remains pending developer guidance and a
separate reviewed catalog PR.

## Completed locally

- Explicit one-off discovery/read/message/reply and persistent opt-out.
- Model/effort-selected ordinary helper creation and scoped, reversible cleanup.
- Continuing two-chat task coordination with readiness, follow-up, result and cleanup
  updates, durable cursors, bounded wait, expiry and message budget.
- Host session identity uses dispatcher/hook kwargs and ctx.session_surface.
- Registration uses documented plugin_data_dir; project metadata queries are read-only.
- The only internal imports shipped are isolated in gateway_compat.py and remain
  visible to Hermes's validator. RPC shape checks fail closed.
- Fictional public examples/test data; private evidence and machine scripts excluded.
- MIT license and upstream attribution retained.

## Required release gates

1. Run the explicit current unit modules listed in README, then privacy_audit.py
   with a machine-local denylist. Neither audit findings nor release manifests
   contain matched private values.
2. Build the exact allowlisted release with build_release.py. Inspect its file list,
   source hashes and reproducible ZIP. No Git metadata, receipts, logs, caches,
   local scripts, credentials or conversation databases may be included.
3. Run Hermes's official validator against that candidate. Keep its remaining
   internal-client warning visible. Validate a clean install separately; a passing
   static/probe report is not proof of all runtime or restart paths.
4. Follow the submitted request linked in UPSTREAM_API_REQUEST.md and obtain a supported ordinary-session Python
   seam or maintainer confirmation before catalog submission. Do not hide imports
   or modify Hermes core to silence lint.
5. Review the candidate, create the public repository and an initial commit, then
   replace the catalog SHA placeholder with the real full 40-character commit.
   No placeholder or invented pin is submission-ready.

The compatibility floor is Hermes 0.22.2, the version reported by the tested live
Desktop gateway. Some installed Python distribution metadata reports an older
version; it is not used as a substitute for the running gateway's contract.
Other platforms and versions, busy-recipient delivery and process-restart recovery
remain outside the live verification scope.

The catalog is a human-reviewed directory. Validation does not guarantee admission.
Read its [submission and lineage rules](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission)
and disclose the original interaction-pattern reference and native transport difference.
