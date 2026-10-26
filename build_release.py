"""Build only allowlisted, privacy-audited text sources. No Git or network mutations."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile
from privacy_audit import PUBLIC_FILES,audit_files


def build(root,denylist=()):
    root=Path(root).resolve();report=audit_files(root,denylist=denylist)
    if not report['ok']:raise ValueError('Public source privacy audit failed; inspect the local audit report.')
    version=re.search(r'^version:\s*["\']?([0-9.]+)',(root/'plugin.yaml').read_text(),re.M).group(1)
    fingerprint=hashlib.sha256(json.dumps(report['manifest'],sort_keys=True).encode()).hexdigest()[:12]
    output=root/'.release'/('local-intercom-'+version+'-'+fingerprint)
    if output.exists():
        check=audit_files(output,denylist=denylist,exact=True)
        if not check['ok'] or check['manifest']!=report['manifest']:raise ValueError('Existing candidate differs; refusing to replace it.')
    else:
        output.mkdir(parents=True)
        for name in PUBLIC_FILES:
            target=output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,target)
    check=audit_files(output,denylist=denylist,exact=True)
    if not check['ok'] or check['manifest']!=report['manifest']:raise ValueError('Release copy does not match audited source.')
    archive=output.parent/(output.name+'.zip')
    if not archive.exists():
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in PUBLIC_FILES:
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                bundle.writestr(info,(output/name).read_bytes())
    with zipfile.ZipFile(archive) as bundle:
        if set(bundle.namelist())!=set(PUBLIC_FILES):raise ValueError('Archive membership mismatch.')
        for entry in report['manifest']:
            if hashlib.sha256(bundle.read(entry['file'])).hexdigest()!=entry['sha256']:raise ValueError('Archive content mismatch.')
    receipt={'ok':True,'directory':str(output),'archive':str(archive),'file_count':len(PUBLIC_FILES),
             'zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'manifest':report['manifest']}
    (root/'release-candidate.local.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return receipt


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--denylist',type=Path);args=parser.parse_args()
    denylist=json.loads(args.denylist.read_text(encoding='utf-8-sig')) if args.denylist else []
    result=build(Path(__file__).parent,denylist)
    print(json.dumps({k:v for k,v in result.items() if k!='manifest'},indent=2))

if __name__=='__main__':main()
