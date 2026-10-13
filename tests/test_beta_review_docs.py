"""Post-build evidence docs must not invalidate otherwise identical installers."""
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def release_gate(changed):
 source=(ROOT/'.github/workflows/beta-release-review.yml').read_text()
 allowed=next(line.strip() for line in source.splitlines() if line.strip().startswith('allowed='))
 exec(allowed+'\nassert changed<=allowed',{'changed':set(changed)})

def test_review_docs_can_follow_unchanged_candidate():
 release_gate(['docs/milestones/Keyframe-M5-plan.md',
               'docs/milestones/Keyframe-M5-results.md',
               'docs/milestones/Keyframe-0.5-design.md',
               'tests/test_beta_review_docs.py'])

@pytest.mark.parametrize('path',['gui/window.py','slide_core/version.py','packaging/SlideExtractor.spec',
 'packaging/native-sources.lock.json','requirements.txt','tests/test_product_keyframes.py'])
def test_review_docs_exception_does_not_allow_runtime_or_build_changes(path):
 with pytest.raises(AssertionError):release_gate([path])

def version_gate(version):
 import re
 source=(ROOT/'.github/workflows/beta-release-review.yml').read_text()
 statement=next(line.strip() for line in source.splitlines()
                if 'assert re.fullmatch' in line and "c['version']" in line)
 exec(statement,{'re':re,'c':{'version':version}})

@pytest.mark.parametrize('version',['0.5.0b1','0.4.12rc1'])
def test_candidate_prerelease_identity_is_accepted(version):
 version_gate(version)

@pytest.mark.parametrize('version',['0.5.0b1/path','v0.5.0b1','0.5.0b','0.5.0'])
def test_candidate_version_gate_rejects_unsafe_or_nonprerelease(version):
 with pytest.raises(AssertionError):version_gate(version)
