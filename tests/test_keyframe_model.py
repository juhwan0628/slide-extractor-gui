"""Keyframe observation model, exact clock and provenance contracts."""
from dataclasses import fields,replace
from fractions import Fraction
from pathlib import Path
import pytest
from slide_core.models import Sample,Project,AnalysisRequest,AnalysisResult,SourceRef,DisplayTransform,make_export_snapshot

def source():
 return SourceRef(Path('/tmp/keyframe-model.mp4'),10,1,0,80,48,DisplayTransform(80,48),
  metadata=(('time_base_num',1),('time_base_den',90000),('origin_pts',90000),('duration_s',3)))

def observations():
 return tuple(Sample(f's{i}',ordinal=i,source_pts=pts,time_base=Fraction(1,90000),
  cache_path=f'{i}.jpg',width=80,height=48,pts_origin=90000)
  for i,pts in enumerate((90000,90009,180000)))

def test_sample_contract_has_no_grid_or_nominal_timestamp():
 assert not {'grid_index','nominal_time'} & {f.name for f in fields(Sample)}
 assert 'ordinal' in {f.name for f in fields(Sample)}
 ss=observations()
 assert [s.actual_time for s in ss]==[0,Fraction(1,10000),1]
 assert Project(source(),samples=ss).sampling_algorithm=='decoder-keyframes-v1'

@pytest.mark.parametrize('boundary',['project','request','result','snapshot'])
@pytest.mark.parametrize('defect',['ordinal','clock','origin','pts'])
def test_observation_sequence_validated_at_every_boundary(boundary,defect):
 ss=observations()
 bad={'ordinal':replace(ss[1],ordinal=0),
      'clock':replace(ss[1],time_base=Fraction(1,90001)),
      'origin':replace(ss[1],pts_origin=89999),
      'pts':replace(ss[1],source_pts=ss[0].source_pts)}[defect]
 values=(ss[0],bad,ss[2])
 with pytest.raises(ValueError):
  if boundary=='request':AnalysisRequest(source(),None,values)
  elif boundary=='result':AnalysisResult(values,(),())
  elif boundary=='project':Project(source(),samples=values)
  else:
   project=Project(source());project.samples=values;make_export_snapshot(project)

def test_project_clock_must_match_source_metadata():
 ss=tuple(replace(s,pts_origin=89900) for s in observations())
 with pytest.raises(ValueError,match='source'):Project(source(),samples=ss)

def test_snapshot_keeps_algorithm_and_immutable_observations():
 p=Project(source(),samples=observations())
 snap=make_export_snapshot(p)
 assert snap.sampling_algorithm==p.sampling_algorithm=='decoder-keyframes-v1'
 p.samples=()
 assert len(snap.samples)==3
 with pytest.raises(ValueError,match='algorithm'):
  Project(source(),sampling_algorithm='bucket-first-v1')

@pytest.mark.parametrize('ordinal',[-1,True,1.5])
def test_invalid_ordinal_rejected(ordinal):
 with pytest.raises(ValueError):
  Sample('s',ordinal,90000,Fraction(1,90000),'x.jpg',80,48,90000)
