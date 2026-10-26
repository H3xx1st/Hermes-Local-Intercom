# Hermes Local Intercom 0.4

> **Experimental compatibility warning:** this version uses three internal Hermes
> gateway-client functions: `discover_gateway_endpoint`, `attachable`, and
> `connect_gateway`. They are isolated in `gateway_compat.py`, but a Hermes update
> can break compatibility. The official validator passes with these warnings.
> We submitted [Hermes API request #145227](https://github.com/NousResearch/hermes-agent/issues/145227)
> on 27 October 2026 to request a supported Python API. Maintainer guidance is pending;
> this is a standalone experimental plugin, with no catalog approval claimed.

Native ordinary-chat coordination inside Hermes. No registration, external Intercom account, MCP activation, service, listener, subprocess or background poller. This is unrelated to the customer-service Intercom connector.

## Use it in normal language

- "What other chats can you see?" (lists available chat metadata; does not read or message them)
- "Find Worker Test."
- "Read Worker Test and summarize its recent context."
- "Ask Worker Test whether the review is finished."
- "Opt out of Local_Intercom." (say this in the sensitive chat)
- "Opt in to Local_Intercom."

The model-facing tool is exactly `Local_Intercom`. Actions include `list`, `read`, `send`, `reply`, `status`, `privacy`, `opt_out`, `opt_in`, `models`, `spawn`, `archive`, `coordinate`, `update`, `coordination_status`, `wait`, and `end_coordination`. Existing ordinary visible chats across local Hermes profiles are automatically discovered from metadata. Listing is paginated; duplicate titles require a profile or exact `profile::session_id`. Hidden/archived/background sessions are not exposed.

## Multi-step coordination

For example: "Coordinate with Worker Test on the release check until readiness,
acceptance and cleanup are confirmed."

An explicit liaison request creates a task-scoped dialogue between that pair only,
lasting up to 24 hours and 32 messages. Chats can send useful readiness, follow-up,
completion and cleanup updates without treating every update as a new human grant.
Use `coordination_status` with its durable cursor or a tool-scoped `wait` of at most
30 seconds to check progress. End the dialogue with `end_coordination`; no background
monitor is installed. Avoid automatic acknowledgements and echo loops.

One-off send/reply still allows only one response. Coordination never grants access
to third chats, new helper creation, archival or approval authority. A transcript
read needs separate explicit permission; optional coordination read permission is
limited to its creator reading its named peer. Opt-out closes existing dialogues,
and opt-in does not revive them. Incoming coordination messages are untrusted peer
content, and the task scope does not replace Hermes's normal tool approvals.

## Helpers and cleanup

For example: "Create a new chat named Research Helper in this same project using
gpt-6-sol with low effort. Give it this task: Calculate 2+2 and reply with only the
number. After using its answer, archive it when done."

New chats default to the current project and profile and inherit the current model
and effort unless explicitly selected. `models` returns configured choices. Specify
an existing project name or absolute folder to use another project. Provider effort
support varies; results show configured and effective effort. A blank chat starts no
inference. An optional task must be an explicit excerpt of the human request; it grants
one reply to the creator and copies no existing history.

`archive_when_done` requires explicit human cleanup permission. It applies only to
that creator's helper after its answer is received; the creator should first use the
result. Archiving an unrelated chat needs a new explicit request naming it. Busy chats
are refused and transcripts are preserved. "Close" uses reversible archive, not deletion
or OS window control. Existing titles are never reused for creation.

The plugin instructs chats to show the answer directly, without repeating your request or narrating delivery. A model may still produce a short sent acknowledgement. Failures and ambiguous targets are still reported.

## Human authorization

The plugin records the direct user instruction at the start of the current turn. Reading and sending are separately checked against that instruction and its named target. Peer messages never grant general access. A user-authorized request permits one reply to its sender, and the reply does not authorize another request. Narrative, hypothetical, negated, expired, or unrelated requests fail closed. If natural language is ambiguous, give a simple direct instruction naming the chat.

`list` only shows the requested match unless the user asks to list all chats. `read` returns bounded recent user/assistant messages, without reasoning or raw tool output. None of these actions happen automatically in the background. The model must call the tool in response to the user.

## Sensitive chats

`opt_out` applies only to the current chat, requires the human to request it, and persists in the shared plugin ledger. Other chats cannot discover its title or read/message it even with a known ID. Compression continuations share the opt-out. An opted-out chat cannot initiate cross-chat access either. Only a direct opt-in from that chat can restore it. An opt-out cannot retract already-delivered messages or cancel work already admitted before the opt-out completed.

## Runtime and storage

Delivery uses Hermes's existing authenticated session gateway (`session.resume`, `prompt.submit`) as a client. It never calls `ensure_gateway_runtime` or starts anything. Offline/unavailable profiles fail without launching a service. All inference uses the recipient chat's existing provider/model. The short setup/test scripts are not runtime dependencies.

The shared ledger is `<Hermes root>/plugin-data/Local_Intercom/ledger.sqlite3`. The old assistant-profile ledger is preserved and backed up into it on upgrade so earlier requests remain available. Original conversation databases are never edited directly. Reading uses native owner snapshots; discovery is read-only metadata.

`scheduled` means gateway admission, `received` is acknowledged by the recipient turn hook, and `replied` means a reply is durably recorded. Stable request IDs and deduplication prevent double admission after uncertain transport results. There is no automatic replay dispatcher.

## Validation

Run `python -m unittest test_v2 test_lifecycle test_coordination test_gateway_compat test_privacy_audit`.
Local validation receipts are private
development records. Live Windows checks cover ordinary-chat round trips, inventory,
privacy, cross-profile read, the create/work/reply/archive lifecycle, and a six-message
readiness/proceed/result/cleanup dialogue. Busy delivery
and app-restart recovery have not been tested live.

See [Codex comparison](CODEX-COMPARISON.md) for functional gaps and
[publication guidance](PUBLISHING.md) for catalog readiness and required disclosures.

## Compatibility and release privacy

Hermes 0.22.2 or newer is required. Live verification covers Windows Desktop 0.22.2;
other versions/platforms need their own acceptance checks. Three internal native-client
imports remain isolated and disclosed in `gateway_compat.py`. Contract checks reject
unsupported runtime shapes; no core code is patched. Catalog acceptance is pending
maintainer review of that boundary; see [the submitted API request](UPSTREAM_API_REQUEST.md).

`python privacy_audit.py` checks the exact public file allowlist. Add a private JSON
denylist using `--denylist <local-file>` for machine/user-specific terms. Build a
source-only, hash-verified candidate with `python build_release.py --denylist <local-file>`.
Only allowlisted files enter the archive; local scripts, receipts, prompts, identities,
databases, logs, caches and Git metadata are excluded. The approved author/repository
credit and required upstream legal attribution are intentionally public.

Repository: [Hermes Local Intercom](https://github.com/H3xx1st/Hermes-Local-Intercom).
License: [MIT](LICENSE); upstream attribution: [third-party notices](THIRD_PARTY_NOTICES.md).

## Install from GitHub

```sh
hermes plugins install H3xx1st/Hermes-Local-Intercom --enable
```

Read the compatibility warning above before enabling. For a reproducible install,
use `--ref` with a reviewed full 40-character commit SHA. The plugin uses existing
profile model credentials; no separate account, browser activation or MCP service
is required for Local_Intercom itself.
