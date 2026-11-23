"""Exercise the real snapshot-bound test dependency copier on synthetic files."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_release


class BuildTestDependencies(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='mattersyn-test-dependencies-')
        self.root=Path(self.tmp.name)
        self.source=self.root/'source'
        self.work=self.root/'candidate/project/recipe-atlas'
        self.work.mkdir(parents=True)
        self.rows=[]
        for i,relative in enumerate(build_release.TEST_MODULE_INPUTS):
            path=self.source/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(('# synthetic authored dependency '+str(i)+'\n').encode())
            self.rows.append({'path':relative,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})

    def tearDown(self):
        self.tmp.cleanup()

    def copy(self,rows=None):
        build_release.copy_test_dependencies(self.source,self.work,{'input_files':self.rows if rows is None else rows})

    def test_exact_dependencies_keep_repository_layout_and_stay_out_of_dist(self):
        self.assertEqual(set(build_release.TEST_MODULE_INPUTS),{
            'tools/simple-pipeline/to_site.py','tools/simple-pipeline/local_caption_backfill.py',
            'tools/simple-pipeline/completeness_policy.py','tools/simple-pipeline/completeness_policy.json',
            'tools/simple-pipeline/chemical_name_card_identity.py','tools/simple-pipeline/starting_particle_roles.py',
            'tools/simple-pipeline/completeness_identity.py',
            'tools/package-importer/importer.py','tools/package-importer/preflight.py'})
        self.copy()
        for relative in build_release.TEST_MODULE_INPUTS:
            self.assertEqual((self.work.parent/relative).read_bytes(),(self.source/relative).read_bytes())
        self.assertEqual(len(list((self.work.parent/'tools').rglob('*.py'))),8)
        self.assertTrue((self.work.parent/'tools/simple-pipeline/completeness_policy.json').is_file())
        self.assertFalse((self.work/'dist/tools').exists())

    def test_missing_required_row_rejects_before_any_dependency_copy(self):
        with self.assertRaisesRegex(ValueError,'Missing or duplicate'):
            self.copy(self.rows[:1])
        self.assertFalse((self.work.parent/'tools').exists())

    def test_duplicate_required_row_is_not_a_replacement_approval(self):
        with self.assertRaisesRegex(ValueError,'Missing or duplicate'):
            self.copy(self.rows+[dict(self.rows[0])])
        self.assertFalse((self.work.parent/'tools').exists())

    def test_changed_authored_bytes_reject_before_any_dependency_copy(self):
        (self.source/build_release.TEST_MODULE_INPUTS[1]).write_bytes(b'# changed dependency\n')
        with self.assertRaisesRegex(ValueError,'input hash mismatch'):
            self.copy()
        self.assertFalse((self.work.parent/'tools').exists())

    def test_missing_authored_file_rejects(self):
        (self.source/build_release.TEST_MODULE_INPUTS[1]).unlink()
        with self.assertRaisesRegex(ValueError,'input hash mismatch'):
            self.copy()
        self.assertFalse((self.work.parent/'tools').exists())

    def test_other_snapshot_tools_are_not_copied(self):
        extra=self.source/'tools/extra.py'
        extra.parent.mkdir(parents=True,exist_ok=True);extra.write_bytes(b'# not a test dependency\n')
        self.copy(self.rows+[{'path':'tools/extra.py','sha256':hashlib.sha256(extra.read_bytes()).hexdigest()}])
        self.assertFalse((self.work.parent/'tools/extra.py').exists())

    def test_dependency_copy_never_rewrites_canonical_input_bytes(self):
        record=self.work/'data/records/audited-synthetic.json'
        record.parent.mkdir(parents=True);raw=b'{"review_status":"source_reviewed","exact":1.000}\r\n';record.write_bytes(raw)
        self.copy()
        self.assertEqual(record.read_bytes(),raw)

    def test_every_dependency_requires_its_own_unique_unchanged_snapshot_row(self):
        for relative in build_release.TEST_MODULE_INPUTS:
            with self.subTest(dependency=relative):
                rows=[row for row in self.rows if row['path']!=relative]
                with self.assertRaisesRegex(ValueError,'Missing or duplicate'):self.copy(rows)
                self.assertFalse((self.work.parent/'tools').exists())
                rows=[dict(row) for row in self.rows]
                next(row for row in rows if row['path']==relative)['sha256']='0'*64
                with self.assertRaisesRegex(ValueError,'input hash mismatch'):self.copy(rows)
                self.assertFalse((self.work.parent/'tools').exists())

    def test_real_consumer_tests_run_in_the_minimal_isolated_candidate_layout(self):
        # Code-only fixture: no site build, real records, figures or paper text.
        rows=[{'path':relative,'sha256':hashlib.sha256((ROOT.parent/relative).read_bytes()).hexdigest()}
              for relative in build_release.TEST_MODULE_INPUTS]
        build_release.copy_test_dependencies(ROOT.parent,self.work,{'input_files':rows})
        paths=('scripts/reader_presentation_registry.py','scripts/reader_source_multipart.py',
               'scripts/public_reader_registry.py','static/reader-presentation-loader.mjs',
               'tests/test_source_reader_multipart.py','tests/test_source_reader_consumers.py')
        for relative in paths:
            target=self.work/relative;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/relative,target)
        result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests',
            '-p','test_source_reader_consumers.py','-v'],cwd=self.work,text=True,capture_output=True,
            encoding='utf-8',env={**os.environ,'PYTHONPATH':'','PYTHONDONTWRITEBYTECODE':'1'})
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.assertIn('Ran 7 tests',result.stderr)
        self.assertNotIn('skipped',result.stderr)
        self.assertFalse((self.work/'dist').exists())

    def test_q_build_uses_the_snapshot_bound_identity_in_the_isolated_candidate(self):
        rows=[{'path':relative,'sha256':build_release.sha(ROOT.parent/relative)}
              for relative in build_release.TEST_MODULE_INPUTS]
        build_release.copy_test_dependencies(ROOT.parent,self.work,{'input_files':rows})
        scripts=self.work/'scripts';scripts.mkdir()
        for source in (ROOT/'scripts').glob('*.py'):
            shutil.copyfile(source,scripts/source.name)
        chemical=self.work/'static/assets/chemical-registry';chemical.mkdir(parents=True)
        (chemical/'registry.json').write_bytes(b'{"entries":[]}')
        (chemical/'bindings.json').write_bytes(b'{"recordBindings":{}}')
        command=("import sys; from pathlib import Path; sys.path.insert(0,'scripts'); "
                 "from reader_background_q import identity_projection; "
                 "alias,ids,records=identity_projection(Path.cwd()); "
                 "assert not ids and not records; "
                 "module=Path(sys.modules[type(alias).__module__].__file__).resolve(); "
                 "assert module==Path.cwd().parent/'tools/simple-pipeline/completeness_identity.py'")
        result=subprocess.run([sys.executable,'-B','-I','-c',command],cwd=self.work,
                              text=True,encoding='utf-8',capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.assertFalse((self.work/'dist').exists())


if __name__=='__main__':
    unittest.main()
