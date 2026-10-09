"""Operation counts catch quadratic GUI work without fragile wall-clock limits."""
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from uuid import uuid4
from PIL import Image
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon,QPixmap
from slide_core import analysis,pts
from slide_core.config import AnalysisSettings
from slide_core.models import Project,SourceRef,DisplayTransform,Sample,Page
from gui.page_model import PageModel
from tests.test_sampling import make_video


def project(tmp_path,count=512):
    samples=tuple(Sample(f's{i}',i,i,Fraction(1),Fraction(i),str(i),80,48) for i in range(count))
    source=SourceRef(tmp_path/'video.mp4',10,1,0,80,48,DisplayTransform(80,48))
    pages=[Page(str(uuid4()),s.sample_id,'manual',None,None,'add') for s in samples]
    return Project(source,samples=samples,pages=pages)


def test_repeated_sample_lookup_has_bounded_work(tmp_path):
    p=project(tmp_path);visits=[]
    class CountedSamples(tuple):
        def __iter__(self):
            for sample in super().__iter__():visits.append(sample.sample_id);yield sample
    p.samples=CountedSamples(p.samples)
    for _ in range(10):assert p.sample_time('s511')==511
    assert len(visits)<=len(p.samples)+10
    p.samples=tuple(replace(s,source_pts=s.source_pts+10) for s in p.samples)
    assert p.sample_time('s511')==521


def test_thumbnail_update_does_not_rescan_pages(tmp_path):
    qt=QApplication.instance() or QApplication([]);p=project(tmp_path)
    visits=[]
    class CountedPages(list):
        def __iter__(self):
            for page in super().__iter__():visits.append(page.page_id);yield page
    p.pages=CountedPages(p.pages);model=PageModel();model.set_project(p);visits.clear();changed=[]
    model.dataChanged.connect(lambda first,last,roles:changed.append((first.row(),last.row())))
    pixmap=QPixmap(16,12);pixmap.fill();model.set_thumbnail('s511',QIcon(pixmap))
    assert changed==[(511,511)]
    assert len(visits)<=len(p.pages)
    target=p.pages[-1].page_id;p.pages=p.pages[:-1];model.sync()
    assert model._page(target) is None


def test_reanalysis_decodes_each_cached_image_once(tmp_path,monkeypatch):
    source=make_video(tmp_path/'video.mp4',duration=4,fps=4)
    settings=AnalysisSettings(roi_mode='full');old,_=analysis.analyze_project(source,settings,tmp_path/'cache')
    original=analysis._read_cache;reads=[]
    def record(sample):reads.append(sample.sample_id);return original(sample)
    monkeypatch.setattr(analysis,'_read_cache',record)
    new,_=analysis.analyze_project(source,settings,tmp_path/'cache',previous=old)
    assert reads==[s.sample_id for s in old.samples]
    assert [p.representative_sample_id for p in old.pages]==[p.representative_sample_id for p in new.pages]
    Path(old.samples[-1].cache_path).write_bytes(b'broken jpeg')
    with pytest.raises(Exception,match='CacheUnavailable'):
        analysis.analyze_project(source,settings,tmp_path/'cache',previous=old)
    assert old.pages


def test_default_extraction_uses_metadata_audit_and_matches_cpu(tmp_path,monkeypatch):
    source=make_video(tmp_path/'video.mp4',duration=2,fps=4,bframes=2)
    samples,_=pts.sample_stream(source,tmp_path/'cache');calls=[];original=pts._ffmpeg
    def record(source,vf,**kwargs):
        cmd=original(source,vf,**kwargs);calls.append(cmd[cmd.index('-vf')+1]);return cmd
    monkeypatch.setattr(pts,'_ffmpeg',record)
    default=pts.extract_selected(source,samples,tmp_path/'default')
    assert calls and all('showinfo@audit=checksum=0' in f for f in calls)
    baseline=pts.extract_selected(source,samples,tmp_path/'baseline',decode_options={'backend':'cpu'})
    for a,b in zip(default,baseline,strict=True):
        with Image.open(a) as x,Image.open(b) as y:assert x.tobytes()==y.tobytes()
