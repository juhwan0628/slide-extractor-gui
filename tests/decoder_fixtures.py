import sys
import time
from types import SimpleNamespace
import pytest
from slide_core import pts
from slide_core.media import MediaError
from slide_core.models import CancelToken

def decoder(monkeypatch, tmp_path, body):
    script=tmp_path/'decoder.py'
    script.write_text('import sys,time\n'+body)
    monkeypatch.setattr(pts,'_ffmpeg',lambda *a,**kw:[sys.executable,str(script)])
    source=SimpleNamespace(width=2,height=2)
    return source

def sampling_source(monkeypatch,source):
    from fractions import Fraction
    source.metadata=(('time_base_num',1),('time_base_den',1),('origin_pts',0))
    source.transform=SimpleNamespace(sample_aspect_ratio=Fraction(1),rotation=0)
    monkeypatch.setattr(pts,'source_matches',lambda _:True)
    return source
