"""Irregular keyframe JSON and edited-PDF correspondence contracts."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import hashlib,json
from uuid import uuid4
import pytest
from slide_core.models import Sample,Project,Transition,DetectedSegment,Page,make_export_snapshot
from slide_core.config import AnalysisSettings,DetectorConfig
from tests.export_fixtures import make_project
from slide_core.editing import merge_pages,delete_page,add_page,replace_page

def irregular_project(tmp_path,*,late=False):
 p=make_project(tmp_path)
 metadata=dict(p.source.metadata);metadata.update(time_base_num=1,time_base_den=90000,origin_pts=100000,duration_s=3)
 source=replace(p.source,metadata=tuple(metadata.items()))
 pts=(100009,100018,190000,199000) if late else (100000,100009,190000,199000)
 ss=tuple(Sample(f's{i}',i,t,Fraction(1,90000),p.samples[0].cache_path,80,48,100000) for i,t in enumerate(pts))
 t=Transition('b0','s1','s2',ss[1].actual_time,ss[2].actual_time,ss[2].actual_time,'confirmed',2)
 gs=(DetectedSegment('g0',0,1,'s0','s1','s1'),DetectedSegment('g1',1,3,'s2','s3','s3','b0'))
 pages=[Page(str(uuid4()),s.sample_id,'auto',g.segment_id,g.segment_id,'auto') for s,g in zip((ss[1],ss[3]),gs)]
 settings=replace(p.settings,detector=replace(DetectorConfig(),candidate_mad=.01))
 return Project(source,settings,ss,(t,),gs,pages)

def payload(tmp_path,*,late=False):
 from slide_core.keyframe_json import payload_keyframes
 p=irregular_project(tmp_path,late=late);raw=b'synthetic-pdf'
 value=payload_keyframes(make_export_snapshot(p),tmp_path/'수업.pdf',hashlib.sha256(raw).hexdigest(),str(uuid4()))
 return p,value,raw

def test_detailed_json_preserves_pts_ordinal_settings_and_uncertainty(tmp_path):
 from slide_core.keyframe_json import dumps,loads
 p,value,raw=payload(tmp_path)
 assert value['schema_version']==4
 assert value['sampling']['algorithm']=='decoder-keyframes-v1' and 'fps' not in value['sampling']
 assert [s['ordinal'] for s in value['samples']]==list(range(4))
 assert [s['source_pts'] for s in value['samples']]==[100000,100009,190000,199000]
 assert all('grid_index' not in s and 'nominal_timestamp_s' not in s for s in value['samples'])
 assert value['detector']['global_mad']==.01
 boundary=value['detected_boundaries'][0]
 assert boundary['true_boundary_s'] is None and boundary['uncertainty_kind']=='keyframe_and_detector'
 text=dumps(value)
 assert str(tmp_path) not in text and 'cache_path' not in text and '수업.pdf' in text
 assert loads(text,pdf_bytes=raw,pdf_page_count=2,pdf_export_id=value['artifact']['export_id'])==value

def test_first_observation_may_be_after_source_origin(tmp_path):
 from slide_core.keyframe_json import validate
 p,value,_=payload(tmp_path,late=True)
 assert value['samples'][0]['timestamp_s']>0
 assert value['detected_segments'][0]['start_s']==0
 validate(value)

@pytest.mark.parametrize('field,value',[
 ('schema_version',3),('schema_version',True),('duration_s',float('nan')),
 ('duration_s',-1),('duration_kind','/private/path')])
def test_invalid_top_fields_rejected(tmp_path,field,value):
 from slide_core.keyframe_json import validate
 _,data,_=payload(tmp_path);data[field]=value
 with pytest.raises(ValueError):validate(data)

@pytest.mark.parametrize('section,index,key,value',[
 ('samples',0,'ordinal',True),('samples',1,'ordinal',0),
 ('samples',1,'source_pts',100000),('samples',0,'timestamp_s',1),
 ('samples',0,'cache_width',False),('samples',0,'cache_path','/tmp/private'),
 ('detected_boundaries',0,'true_boundary_s',.5),('detected_boundaries',0,'right_sample_id','missing'),
 ('detected_boundaries',0,'lower_s',.9),('detected_boundaries',0,'uncertainty_kind','exact'),
 ('detected_segments',0,'first_sample_id','missing'),('detected_segments',0,'end_s',.5),
 ('pages',0,'representative_sample_id','missing'),('pages',1,'pdf_page',1),
 ('pages',0,'representative_timestamp_s',.9),('navigation_ranges',0,'is_slide_boundary',True),
 ('navigation_ranges',1,'start_s',0)])
def test_bad_types_references_or_fields_rejected(tmp_path,section,index,key,value):
 from slide_core.keyframe_json import validate
 _,data,_=payload(tmp_path);data[section][index][key]=value
 with pytest.raises(ValueError):validate(data)

def test_legacy_sampling_and_duplicate_json_fields_rejected(tmp_path):
 from slide_core.keyframe_json import validate,loads,dumps
 _,data,_=payload(tmp_path);old=deepcopy(data)
 old['sampling']['fps']=.5
 with pytest.raises(ValueError):validate(old)
 text=dumps(data).replace('"schema_version": 4','"schema_version": 4, "schema_version": 4')
 with pytest.raises(ValueError,match='duplicate'):loads(text)

def test_pdf_identity_and_artifact_privacy_rejected(tmp_path):
 from slide_core.keyframe_json import validate
 _,data,raw=payload(tmp_path)
 for facts in ({'pdf_bytes':b'changed'},{'pdf_page_count':1},{'pdf_export_id':str(uuid4())}):
  with pytest.raises(ValueError):validate(data,**facts)
 data['artifact']['generator_version']='/home/private'
 with pytest.raises(ValueError):validate(data)

def test_edits_preserve_detected_track_and_simple_follows_pdf_navigation(tmp_path):
 from slide_core.keyframe_json import payload_keyframes,validate
 from slide_core.simple_json import simple_timeline
 p,data,_=payload(tmp_path);boundaries=deepcopy(data['detected_boundaries'])
 merge_pages(p,[x.page_id for x in p.pages])
 simple=simple_timeline(p)
 assert simple=={'slides':[{'page':1,'start':0,'end':3}]}
 after=payload_keyframes(make_export_snapshot(p),'out.pdf','0'*64,str(uuid4()))
 assert after['detected_boundaries']==boundaries and len(after['pages'])==1
 assert after['pages'][0]['representative_timestamp_s']==1.1
 add_page(p,0);replace_page(p,p.pages[0].page_id,Fraction(1,10000))
 after=payload_keyframes(make_export_snapshot(p),'out.pdf','0'*64,str(uuid4()));validate(after)
 for row in after['pages']:
  sid=row['representative_sample_id'];s=next(s for s in after['samples'] if s['sample_id']==sid)
  assert row['representative_timestamp_s']==s['timestamp_s']
 simple=simple_timeline(p)
 assert simple['slides'][0]['start']==0 and simple['slides'][0]['end']==1.1
 assert simple['slides'][1]['start']==1.1

def test_large_integer_pts_preserved_without_float_reconstruction(tmp_path):
 from slide_core.keyframe_json import payload_keyframes,dumps,loads
 p=make_project(tmp_path);origin=2**53+5
 p.source=replace(p.source,metadata=tuple({**dict(p.source.metadata),'origin_pts':origin}.items()))
 p.samples=(replace(p.samples[0],source_pts=origin,pts_origin=origin),)
 value=payload_keyframes(make_export_snapshot(p),'out.pdf','0'*64,str(uuid4()))
 decoded=loads(dumps(value))
 assert decoded['samples'][0]['source_pts']==origin and decoded['source']['origin_pts']==origin


def test_json_accepts_same_near_threshold_mask_projection_as_runtime_analysis(tmp_path):
 from slide_core.keyframe_json import validate
 from slide_core.roi import build_detection_region
 from slide_core.models import Rect
 roi=Rect(0,0,1920,1070);mask=Rect(0,0,1920,1009)
 region=build_detection_region(1920,1080,640,360,roi,mask)
 assert region.valid.shape==(178,320) and int(region.valid.sum())==2880
 _,data,_=payload(tmp_path)
 data['source'].update(coded_width=1920,coded_height=1080,display_width=1920,display_height=1080)
 for sample in data['samples']:sample.update(cache_width=640,cache_height=360)
 data['roi']={'x':0,'y':0,'width':1920,'height':1070}
 data['ignore_masks']=[{'x':0,'y':0,'width':1920,'height':1009}]
 assert validate(data) is data
