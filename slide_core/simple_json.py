"""Minimal, user-facing slide timeline. No source/debug metadata."""
from __future__ import annotations
import json
from pathlib import Path

def simple_timeline(project):
    project.validate()
    segments={s.segment_id:s for s in project.segments}
    entries=[]
    for idx,page in enumerate(project.pages,1):
        t=project.sample_time(page.representative_sample_id)
        segment=next((seg for seg in project.segments if seg.start_time<=t<seg.end_time),None)
        if segment is None:
            raise ValueError('Page cannot be mapped to a detected slide interval')
        entries.append(dict(page=idx,start=round(float(segment.start_time),9),
                            end=round(float(segment.end_time),9)))
    return dict(slides=entries)

def encode_simple(project):
    return (json.dumps(simple_timeline(project),ensure_ascii=False,indent=2,
                       allow_nan=False)+'\n').encode('utf-8')
