# Attribution and provenance

Local_Intercom was developed after reviewing the interaction pattern in
[majordave/hermes-intercom](https://github.com/majordave/hermes-intercom), which
credits the architecture proposed in
[NousResearch/hermes-agent#81885](https://github.com/NousResearch/hermes-agent/issues/81885).
The implementation here uses ordinary native gateway chats, explicit task-scoped
permissions and reversible helper lifecycle controls instead of a per-session
Unix socket registry. It does not vendor the original plugin's modules or socket
transport. The historical experimental implementation is not included in the release.

The original project's notice is retained conservatively for this adaptation.
Its license was checked at the public repository's LICENSE on 27 October 2026.

## hermes-intercom

MIT License

Copyright (c) 2026 David Absalon Duarte Dyck (majordave)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
