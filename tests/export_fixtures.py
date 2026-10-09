"""Synthetic current-model export fixtures, never legacy timestamp engines."""
from fractions import Fraction
from uuid import uuid4
from pathlib import Path
from PIL import Image
from slide_core.models import SourceRef,DisplayTransform,Sample,Page,Project,Rect,DetectedSegment
from slide_core.config import AnalysisSettings
from slide_core.media import fingerprint_source


def make_project(root):
    root=Path(root);source=root/'input.mp4';source.write_bytes(b'original synthetic video')
    stat=source.stat();ref=SourceRef(source,stat.st_size,stat.st_mtime_ns,0,80,48,
        DisplayTransform(80,48),fingerprint_source(source),
        metadata=(('codec','synthetic'),('time_base_num',1),('time_base_den',1),
                  ('origin_pts',0),('duration_s',2),('duration_kind','video_metadata')))
    image=root/'frame.png';Image.new('RGB',(80,48),'red').save(image)
    sample=Sample('s0',0,0,Fraction(1),Fraction(0),str(image),80,48)
    page=Page(str(uuid4()),'s0','manual',None,'g0','insert')
    return Project(ref,AnalysisSettings(roi_mode='full',effective_roi=Rect(0,0,80,48)),
                   samples=(sample,),segments=(DetectedSegment('g0',0,2,'s0','s0','s0'),),pages=[page])


def extract_stub(project):
    def extract(source,selections,output_root,**kwargs):
        return tuple(Path(project.samples[0].cache_path) for _ in selections)
    return extract
