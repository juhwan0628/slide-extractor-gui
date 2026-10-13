from fractions import Fraction
import numpy as np
import pytest
from slide_core.spatial_groups import spatial_detect
from slide_core.config import SpatialConfig
from slide_core.models import Sample

def run(a,mask=None,**kwargs):
    samples=tuple(Sample(str(i),i,i,Fraction(1),str(i),100,100) for i in range(len(a)))
    return samples,spatial_detect(samples,iter(a),duration=len(a),valid_mask=np.ones(a.shape[1:],bool) if mask is None else mask,config=SpatialConfig(),**kwargs)

def test_brief_slide_and_return():
    a=np.full((3,100,100),255,np.uint8);a[1,:70,:70]=0
    s,(t,g)=run(a)
    assert [x.observed_time for x in t]==[1,2]
    assert all(x.reason=='spatial_change' and x.persistence_samples==1 for x in t)
    assert [x.representative_sample_id for x in g]==['0','1','2']

def test_local_writing_one_group():
    a=np.full((4,100,100),255,np.uint8)
    for i in range(1,4):a[i,:5,:i*10]=0
    s,(t,g)=run(a)
    assert not t and len(g)==1 and g[0].representative_sample_id=='2'

def test_sparse_distributed_boundary():
    a=np.full((2,100,100),255,np.uint8)
    for y in range(0,100,20):
        for x in range(0,100,20):a[1,y:y+5,x:x+5]=0
    assert len(run(a)[1][1])==2

def test_mask_excludes_changes():
    a=np.full((2,100,100),255,np.uint8);a[1,:70,:70]=0
    mask=np.ones((100,100),bool);mask[:70,:70]=False
    assert len(run(a,mask)[1][1])==1

def test_cancel_during_staging_closes_stage(monkeypatch):
    import slide_core.spatial_groups as module
    opened=[];real=module.tempfile.TemporaryFile
    def tracked(*a,**kw):
        f=real(*a,**kw);opened.append(f);return f
    monkeypatch.setattr(module.tempfile,'TemporaryFile',tracked)
    class Token:
        n=0
        def raise_if_cancelled(self):
            self.n+=1
            if self.n>8:raise RuntimeError('cancel')
    a=np.full((4,100,100),255,np.uint8)
    with pytest.raises(RuntimeError,match='cancel'):run(a,cancel_token=Token())
    assert opened and all(f.closed for f in opened)

def test_invalid_mask_and_cardinality():
    a=np.zeros((2,100,100),np.uint8)
    with pytest.raises(ValueError):run(a,np.zeros((100,100),bool))
    s=tuple(Sample(str(i),i,i,Fraction(1),str(i),100,100) for i in range(2))
    with pytest.raises(ValueError,match='cardinality'):spatial_detect(s,iter(a[:1]),duration=2,valid_mask=np.ones((100,100),bool),config=SpatialConfig())

def test_stage_disk_failure_is_typed_and_closes(monkeypatch):
    import slide_core.spatial_groups as module
    from slide_core.media import MediaError
    class BadStage:
        closed=False
        def __enter__(self):return self
        def __exit__(self,*args):self.closed=True
        def write(self,raw):raise OSError('disk full')
    stage=BadStage()
    monkeypatch.setattr(module.tempfile,'TemporaryFile',lambda **kw:stage)
    with pytest.raises(MediaError,match='DetectionStorageFailed'):run(np.zeros((2,100,100),np.uint8))
    assert stage.closed

def test_reused_supplier_buffer_and_eof():
    a=np.full((2,100,100),255,np.uint8);a[1,:70,:70]=0
    s=tuple(Sample(str(i),i,i,Fraction(1),str(i),100,100) for i in range(2))
    buffer=np.empty((100,100),np.uint8)
    def frames():
        for image in a:
            buffer[:]=image
            yield buffer
    t,g=spatial_detect(s,frames(),duration=2,valid_mask=np.ones((100,100),bool),config=SpatialConfig())
    assert len(g)==2 and t[0].observed_time==1

def test_nonmonotonic_and_extra_observations():
    s=tuple(Sample(str(i),i,0,Fraction(1),str(i),100,100) for i in range(2))
    a=np.zeros((3,100,100),np.uint8)
    with pytest.raises(ValueError,match='Nonmonotonic'):
        spatial_detect(s,iter(a),duration=2,valid_mask=np.ones((100,100),bool),config=SpatialConfig())
    s=tuple(Sample(str(i),i,i,Fraction(1),str(i),100,100) for i in range(2))
    with pytest.raises(ValueError,match='cardinality'):
        spatial_detect(s,iter(a),duration=2,valid_mask=np.ones((100,100),bool),config=SpatialConfig())

@pytest.mark.parametrize('scan',[0,1,2])
def test_cancel_each_rank_scan_closes_stage(monkeypatch,scan):
    import slide_core.spatial_groups as module
    opened=[];real=module.tempfile.TemporaryFile
    def tracked(*a,**kw):
        f=real(*a,**kw);opened.append(f);return f
    monkeypatch.setattr(module.tempfile,'TemporaryFile',tracked)
    class Token:
        n=0
        def raise_if_cancelled(self):
            self.n+=1
            if self.n==10+4*scan:raise RuntimeError('cancel')
    with pytest.raises(RuntimeError,match='cancel'):
        run(np.full((4,100,100),255,np.uint8),cancel_token=Token())
    assert opened[0].closed

def test_progress_distinguishes_grouping_and_selection():
    events=[]
    run(np.full((20,100,100),255,np.uint8),progress=lambda *x:events.append(x))
    assert {e[0] for e in events}=={'grouping','representative_selection'}
    assert [e[1] for e in events]==sorted(e[1] for e in events)
    assert events[-1][1:]==(80,80)
