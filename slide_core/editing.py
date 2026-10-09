"""Atomic, stable-ID page edits for the immutable sample timeline."""
from __future__ import annotations
from bisect import bisect_left
from dataclasses import replace
from fractions import Fraction
from uuid import uuid4
import math

from .models import EditResult, Page, Project


def nearest_sample(project:Project, timestamp):
    if isinstance(timestamp,float) and not math.isfinite(timestamp):
        raise ValueError('timestamp must be finite')
    try:target=Fraction(timestamp)
    except (ValueError,TypeError,OverflowError,ZeroDivisionError) as exc:
        raise ValueError('Invalid timestamp') from exc
    if not project.samples:raise ValueError('No samples')
    samples=project.samples
    times=[s.actual_time for s in samples]
    index=bisect_left(times,target)
    if index==0:return samples[0]
    if index==len(samples):return samples[-1]
    before,after=samples[index-1],samples[index]
    return before if target-before.actual_time<=after.actual_time-target else after


def _derived_segment(project,sample_id):
    time=project.sample_time(sample_id)
    return next((s.segment_id for s in project.segments if s.start_time<=time<s.end_time),None)


def _publish(project,proposed,focus,changed_rows):
    # Validate an isolated provisional Project; publish only when valid.
    candidate=Project(project.source,project.settings,project.samples,project.transitions,
         project.segments,proposed,project.revision+1,project.cache_generation,
         project.analysis_generation)
    project.pages=candidate.pages
    project.revision=candidate.revision
    return EditResult('changed',focus,tuple(changed_rows))


def add_page(project:Project, timestamp):
    sample=nearest_sample(project,timestamp)
    for page in project.pages:
        if page.representative_sample_id==sample.sample_id:
            return EditResult('no_op',page.page_id,(), 'AlreadySelected')
    page=Page(str(uuid4()),sample.sample_id,'manual',None,
              _derived_segment(project,sample.sample_id),'add')
    proposed=sorted((*project.pages,page),key=lambda p:project.sample_time(p.representative_sample_id))
    focus=next(i for i,p in enumerate(proposed) if p.page_id==page.page_id)
    return _publish(project,proposed,page.page_id,(focus,))


def replace_page(project:Project,page_id:str,timestamp):
    page=next((p for p in project.pages if p.page_id==page_id),None)
    if page is None:return EditResult('rejected',None,(),'UnknownPage')
    sample=nearest_sample(project,timestamp)
    if sample.sample_id==page.representative_sample_id:
        return EditResult('no_op',page_id,(),'SameSample')
    if any(p.page_id!=page_id and p.representative_sample_id==sample.sample_id for p in project.pages):
        return EditResult('rejected',page_id,(),'DuplicateSample')
    replacement=replace(page,representative_sample_id=sample.sample_id,
                        derived_segment_id=_derived_segment(project,sample.sample_id),
                        last_edit_kind='replace')
    proposed=sorted((replacement if p.page_id==page_id else p for p in project.pages),
                    key=lambda p:project.sample_time(p.representative_sample_id))
    new_row=next(i for i,p in enumerate(proposed) if p.page_id==page_id)
    old_row=next(i for i,p in enumerate(project.pages) if p.page_id==page_id)
    return _publish(project,proposed,page_id,(old_row,new_row))


def delete_page(project:Project,page_id:str):
    idx=next((i for i,p in enumerate(project.pages) if p.page_id==page_id),None)
    if idx is None:return EditResult('rejected',None,(),'UnknownPage')
    proposed=[p for p in project.pages if p.page_id!=page_id]
    focus=proposed[min(idx,len(proposed)-1)].page_id if proposed else None
    return _publish(project,proposed,focus,(idx,))


def navigate(project:Project, current_id:str|None,delta:int):
    if type(delta) is not int:raise ValueError('Invalid navigation delta')
    if not project.pages:return None
    index=next((i for i,p in enumerate(project.pages) if p.page_id==current_id),0)
    return project.pages[max(0,min(len(project.pages)-1,index+delta))].page_id
