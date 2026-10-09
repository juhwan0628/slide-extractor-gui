import importlib.util
import json
from pathlib import Path


def test_release_gate_rejects_unverified_candidate(tmp_path):
    script=Path(__file__).resolve().parents[1]/'packaging'/'audit_release.py'
    spec=importlib.util.spec_from_file_location('slide_release_audit',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    root=tmp_path/'bundle';root.mkdir()
    bad=tmp_path/'ffmpeg';bad.write_bytes(b'not executable')
    example=Path(__file__).resolve().parents[1]/'packaging'/'binary-manifest.example.json'
    failures=module.audit(root,bad,example)
    assert failures and any('not approved' in x for x in failures)
    assert any('corresponding source archive' in x for x in failures)
    payload=json.loads(example.read_text());payload['status']='APPROVED'
    manifest=tmp_path/'spoof.json';manifest.write_text(json.dumps(payload))
    assert module.audit(root,bad,manifest)
