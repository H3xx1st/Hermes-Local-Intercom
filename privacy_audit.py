"""Fail-closed inspection of the exact public release file set; never print matches."""
import argparse
import hashlib
import json
from pathlib import Path
import re

PUBLIC_FILES=(
    '.gitignore','__init__.py','v2.py','native.py','gateway_compat.py','lifecycle.py','coordination.py',
    'plugin.yaml','README.md','LICENSE','THIRD_PARTY_NOTICES.md','PUBLISHING.md','CODEX-COMPARISON.md',
    'UPSTREAM_API_REQUEST.md','RELEASE_CHECKLIST.md','privacy_audit.py','build_release.py',
    'test_v2.py','test_lifecycle.py','test_coordination.py','test_gateway_compat.py','test_privacy_audit.py',
)
PATTERNS={
    'windows_absolute_path':r'(?i)\b[a-z]:[\\/](?:[a-z0-9_. -]+[\\/])',
    'user_home_path':r'(?i)/(?:home|Users)/[a-z0-9_.-]+/',
    'private_ipv4':r'\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b',
    'actual_chat_identity':r'\blocal-[a-f0-9]{24,}\b',
    'email_address':r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    'credential_token':r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b',
    'credential_assignment':r'''(?i)["']?(?:api[_-]?key|access[_-]?token|password|secret)["']?\s*[:=]\s*["'][^"'{}<>\s]{8,}["']''',
    'private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
}


def audit_files(root,files=PUBLIC_FILES,denylist=(),exact=False):
    root=Path(root).resolve();findings=[];manifest=[];expected=set(files)
    if exact:
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        for name in sorted(actual-expected):findings.append({'file':name,'kind':'unexpected_file'})
    for name in files:
        path=root/name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            findings.append({'file':name,'kind':'missing_or_unsafe_file'});continue
        raw=path.read_bytes()
        if len(raw)>2_000_000 or b'\x00' in raw:
            findings.append({'file':name,'kind':'unexpected_binary_or_large_file'});continue
        try:text=raw.decode('utf-8')
        except UnicodeDecodeError:findings.append({'file':name,'kind':'non_utf8_file'});continue
        manifest.append({'file':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
        for number,line in enumerate(text.splitlines(),1):
            for kind,pattern in PATTERNS.items():
                if re.search(pattern,line):findings.append({'file':name,'line':number,'kind':kind})
            for term in denylist:
                if term and str(term).casefold() in line.casefold():
                    findings.append({'file':name,'line':number,'kind':'local_denylist'})
    return {'ok':not findings,'file_count':len(manifest),'findings':findings,'manifest':manifest,
            'note':'Pattern, allowlist and local denylist checks supplement source review; runtime chat data is never bundled.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('root',nargs='?',default=str(Path(__file__).parent))
    parser.add_argument('--denylist',type=Path);parser.add_argument('--exact',action='store_true')
    parser.add_argument('--output',type=Path);args=parser.parse_args()
    denylist=json.loads(args.denylist.read_text(encoding='utf-8-sig')) if args.denylist else []
    report=audit_files(args.root,denylist=denylist,exact=args.exact)
    if args.output:args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='manifest'},indent=2))
    raise SystemExit(0 if report['ok'] else 1)

if __name__=='__main__':main()
