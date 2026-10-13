import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('m9',Path(__file__).parents[1]/'scripts/benchmark_keyframe_m9.py')
m9=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m9)

def test_summary_uses_median_and_checks_each_mode():
    rows=[dict(source='a',mode='auto',total_s=x,prepare_s=x,analysis_s=x,jpeg_bytes=10,
        observations=2,indexed_keys=3,pages=1,policy='half',backend='native-idr',representatives_s=[1]) for x in (9,1,2)]
    result=m9.summarize(rows)[0]
    assert result['total_s']=={'median':2,'min':1,'max':9}
    rows[-1]['representatives_s']=[2]
    with pytest.raises(ValueError,match='Non-deterministic'):m9.summarize(rows)
