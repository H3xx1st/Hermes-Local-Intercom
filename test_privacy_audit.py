import tempfile
from pathlib import Path
import unittest
from privacy_audit import audit_files

class Tests(unittest.TestCase):
    def setUp(self):
        self.scratch=Path(__file__).parent/'.test-tmp'
        self.scratch.mkdir(exist_ok=True)
    def test_reports_categories_without_echoing_sensitive_values(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            root=Path(folder);secret='gh'+'p_'+'a'*36
            private='C'+':'+chr(92)+'Users'+chr(92)+'example-user'+chr(92)+'file'
            (root/'code.py').write_text(secret+'\n'+private,encoding='utf-8')
            report=audit_files(root,files=('code.py',))
            self.assertFalse(report['ok'])
            self.assertEqual({r['kind'] for r in report['findings']},{'credential_token','windows_absolute_path'})
            self.assertNotIn(secret,str(report));self.assertNotIn(private,str(report))
    def test_unexpected_private_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            root=Path(folder);(root/'code.py').write_text('print(1)');(root/'receipt.json').write_text('{}')
            self.assertFalse(audit_files(root,files=('code.py',),exact=True)['ok'])
    def test_denylist_and_missing_files_fail_closed(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            root=Path(folder);(root/'code.py').write_text('fictional private title')
            self.assertFalse(audit_files(root,files=('code.py',),denylist=['private title'])['ok'])
            self.assertFalse(audit_files(root,files=('missing.py',))['ok'])
    def test_clean_source_is_hashed(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            root=Path(folder);(root/'code.py').write_text('print(1)')
            report=audit_files(root,files=('code.py',),exact=True)
            self.assertTrue(report['ok']);self.assertEqual(len(report['manifest'][0]['sha256']),64)
    def test_generic_literal_credentials_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            root=Path(folder);literal='synthetic'+'-credential'
            (root/'code.py').write_text('api_'+'key = '+repr(literal))
            report=audit_files(root,files=('code.py',))
            self.assertFalse(report['ok'])
            self.assertEqual(report['findings'][0]['kind'],'credential_assignment')
            self.assertNotIn(literal,str(report))

if __name__=='__main__':unittest.main()
