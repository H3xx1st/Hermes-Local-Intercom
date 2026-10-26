# Inter-chat coordination comparison

Checked against the Codex app tools available in this conversation and official
OpenAI documentation on 27 October 2026. No Codex chats were created or messaged
for this comparison.

| Capability | Codex app in this conversation | Local_Intercom |
|---|---|---|
| Discover ordinary chats | list_threads; separate archived listing | Visible ordinary local chats across profiles, excluding opt-outs |
| Read another chat | read_thread with pagination/status summaries | Bounded recent user/assistant context; explicit named human request |
| Send to an existing chat | send_message_to_thread with human authorization | Explicit named-human send; one authorized reply returns automatically |
| Cross-project coordination | Supported by app tools | Live verified between two projects |
| Create ordinary chat with model/effort | create_thread model/thinking and project options | spawn with model/effort; same profile/project defaults; live verified |
| Delegate and clean up helper | App chat creation and archive; separate agent orchestration tools | Explicit task plus scoped archive_when_done grant; live verified |
| Per-chat opt-out | No matching intercom opt-out control in the tools inspected | Persistent privacy opt-out; live verified |
| Wait for multiple results/progress | wait_threads, read_thread status | Cursor-based task status and bounded wait; no wait-many tool |
| Continue, steer or interrupt work | Follow-up messaging and agent controls | Scoped task updates; no steering/interrupt API |
| Fork history | fork_thread | Fresh chats only, no automatic history copy |
| Git worktree isolation / handoff | Dedicated app tools | No worktree or handoff integration |
| Restore archived chats | set_thread_archived(false) | Restore through Hermes UI; plugin currently exposes archive only |
| Repeated task dialogue | Authorization-dependent | Explicit human coordination grant, pair/task bound, 24h/32 messages; one-off send remains one reply |

The ordinary chat workflow is comparable for discovery, recent context, question/reply,
model-selected helper creation and scoped cleanup. It does not provide the broader
Codex orchestration/runtime features above. Receiving a message does not grant a peer
general authority to read other chats or create more work.

A reviewed controller/peer workflow used readiness requests, safe-handoff confirmation,
completion receipts and cleanup acknowledgements over several turns. The release's
disposable live check reproduced that communication pattern as six received messages:
task -> READY -> PROCEED -> RESULT 4 -> CLEANUP -> CLEANUP CONFIRMED, then closed the
dialogue. The comparison retains no private thread titles, IDs, paths or message bodies.

OpenAI documents [subagent model/effort selection and orchestration](https://learn.chatgpt.com/docs/agent-configuration/subagents).
Its [app-server reference](https://learn.chatgpt.com/docs/app-server) documents thread
listing/reading/creation/forking/archiving and turn steering/interruption. Ordinary
user-owned chats and execution subagents are distinct surfaces; this plugin creates
ordinary Hermes chats.
