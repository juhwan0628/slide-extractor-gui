"""Known-truth GOP validation; limitations are not repaired with FPS fallback."""
import subprocess
import pytest
from slide_core.media import probe_source
from slide_core.analysis import analyze_project
from slide_core.config import AnalysisSettings

def lecture(path,gop):
 # A 0..5, short B 5..7, A 7..15, final C 15..22 seconds.
 # lavfi keeps the fixture independent of optional image input decoders.
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
  '-f','lavfi','-i','color=c=red:s=160x90:r=5:d=5',
  '-f','lavfi','-i','color=c=lime:s=160x90:r=5:d=2',
  '-f','lavfi','-i','color=c=red:s=160x90:r=5:d=8',
  '-f','lavfi','-i','color=c=blue:s=160x90:r=5:d=7',
  '-filter_complex','[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0,fps=5,format=yuv420p[v]',
  '-map','[v]','-c:v','mpeg4','-g',str(gop),'-keyint_min',str(gop),'-sc_threshold','1000000000',str(path)],check=True,timeout=30)
 return probe_source(path)

@pytest.mark.parametrize('gop,expected',[ (5,True),(50,False) ])
def test_known_short_slide_present_only_when_observed_keyframes(tmp_path,gop,expected):
 source=lecture(tmp_path/'lecture.mp4',gop)
 p,_=analyze_project(source,AnalysisSettings(roi_mode='full'),tmp_path/'cache')
 try:
  assert p.sampling_algorithm=='decoder-keyframes-v1'
  green_samples=[s for s in p.samples if 5<=s.actual_time<7]
  assert bool(green_samples) is expected
  byid={s.sample_id:s for s in p.samples}
  green_pages=[page for page in p.pages if 5<=byid[page.representative_sample_id].actual_time<7]
  assert bool(green_pages) is expected
  assert any(byid[page.representative_sample_id].actual_time>=15 for page in p.pages)
  assert all(s.ordinal==i for i,s in enumerate(p.samples))
  if not expected:assert [float(s.actual_time) for s in p.samples]==[0,10,20]
 finally:p._cache_pin.close()
