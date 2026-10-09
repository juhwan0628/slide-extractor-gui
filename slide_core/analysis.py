"""Qt-free M3 coordinator: transactional project adoption after valid results."""
from __future__ import annotations
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from uuid import uuid4
from PIL import Image
import cv2
import numpy as np

from .config import AnalysisSettings,DetectorConfig
from .media import probe_source,source_matches,MediaError
from .pts import sample_stream
from .roi import automatic_roi,build_detection_region
from .models import Project,AnalysisResult,Page,Rect
from .transitions import streaming_detect
from .profiling import AnalysisProfile,measured


def _read_cache(sample):
    path=Path(sample.cache_path)
    if not path.is_file() or path.is_symlink():
        raise MediaError('CacheUnavailable: missing cache image',code='CacheUnavailable')
    try:
        with Image.open(path) as img:
            result=np.asarray(img.convert('RGB'))
    except (OSError,ValueError) as exc:
        raise MediaError('CacheUnavailable: corrupt JPEG',code='CacheUnavailable') from exc
    if result.shape!=(sample.height,sample.width,3):
        raise MediaError('CacheUnavailable: JPEG dimensions changed',code='CacheUnavailable')
    return result


def _prepared(samples,region,profile=None,cancel_token=None):
    cache=region.cache_roi
    for sample in samples:
        if cancel_token is not None:cancel_token.raise_if_cancelled()
        with measured(profile,'cache_prepare'):
            rgb=_read_cache(sample)
            roi=rgb[cache.y:cache.y+cache.height,cache.x:cache.x+cache.width]
            if not roi.size:raise ValueError('Empty ROI')
            gray=cv2.cvtColor(roi,cv2.COLOR_RGB2GRAY)
            shape=region.valid.shape
            prepared=cv2.resize(gray,(shape[1],shape[0]),interpolation=cv2.INTER_AREA)
        yield prepared


def _resolve_roi(samples,settings,source,cancel_token=None):
    if not samples:raise ValueError('No decoded samples')
    cw,ch=samples[0].width,samples[0].height
    dw,dh=source.transform.display_width,source.transform.display_height
    if settings.roi_mode=='auto':
        images=[]
        for sample in samples[:8]:
            if cancel_token is not None:cancel_token.raise_if_cancelled()
            images.append(_read_cache(sample))
        proposal,reason=automatic_roi(images)
        # proposal is in cached coordinates. Convert to full display conservatively.
        from math import floor,ceil
        roi=Rect(floor(proposal.x*dw/cw),floor(proposal.y*dh/ch),
                 min(dw-floor(proposal.x*dw/cw),ceil(proposal.width*dw/cw)),
                 min(dh-floor(proposal.y*dh/ch),ceil(proposal.height*dh/ch)))
    elif settings.roi_mode=='full':
        roi=Rect(0,0,dw,dh)
    else:
        roi=settings.effective_roi
    masks=settings.masks
    if len(masks)>1:raise ValueError('At most one exclusion mask is supported')
    region=build_detection_region(dw,dh,cw,ch,roi,masks[0] if masks else None)
    return roi,region


def _settings_key(settings):
    """Canonical identity independent of transient GUI settings revision."""
    return (settings.fps,settings.roi_mode,
            settings.effective_roi if settings.roi_mode=='manual' else None,
            tuple(settings.masks),settings.detector or DetectorConfig())


def _analyze_project(source,settings:AnalysisSettings,cache_root,*,previous:Project|None=None,
                    cancel_token=None,sampler=sample_stream,progress=None,profile=None,decode_options=None):
    """Return a new validated project without modifying previous on error/cancel.

    Reuses immutable cached Samples when fps/source are unchanged. Stale source or
    incomplete sample caches fail closed, never silently reuse previous results.
    """
    from .models import CancelledError
    if cancel_token is not None:cancel_token.raise_if_cancelled()
    source=probe_source(Path(source),cancel_token=cancel_token) if not hasattr(source,'fingerprint') else source
    if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
    cache_generation=str(uuid4())
    reused=False
    if previous is not None and previous.source!=source:
        raise MediaError('SourceChanged: project source identity mismatch',code='SourceChanged')
    if previous is not None and previous.source==source and previous.settings is not None:
        if previous.settings.fps==settings.fps:
            samples=previous.samples
            if not samples:raise MediaError('CacheUnavailable',code='CacheUnavailable')
            # _prepared validates every JPEG while decoding it for detection.
            # The result is adopted only after that iterator is fully consumed.
            cache_generation=previous.cache_generation
            reused=True
        else:samples=()
    else:samples=()
    created_cache=None
    if progress:progress('sampling',None,None)
    try:
        if not reused:
            extra={'profile':profile,'decode_options':decode_options} if sampler is sample_stream else {}
            with measured(profile,'sampling'):
                samples,created_cache=sampler(source,Path(cache_root),fps=Fraction(str(settings.fps)),
                                             cancelled=cancel_token,**extra)
                samples=tuple(samples)
        if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
        if progress:progress('detecting',0,len(samples))
        if profile is not None:
            profile.metadata.update(cache_reused=reused,sample_count=len(samples),sample_fps=settings.fps,
                                    width=source.width,height=source.height,duration_s=float(dict(source.metadata)['duration_s']))
        with measured(profile,'roi'):
            roi,region=_resolve_roi(samples,settings,source,cancel_token)
        prepared=_prepared(samples,region,profile,cancel_token)
        if progress:
            original_prepared=prepared
            def observed():
                for i,image in enumerate(original_prepared):
                    if i%16==0:progress('detecting',i,len(samples))
                    yield image
            prepared=observed()
        metadata=dict(source.metadata)
        duration=Fraction(str(metadata['duration_s']))
        detector=settings.detector or DetectorConfig()
        with measured(profile,'detection'):
            transitions,segments=streaming_detect(samples,prepared,duration=duration,
                                                  valid_mask=region.valid,config=detector)
        if cancel_token is not None:cancel_token.raise_if_cancelled()
        if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
        if progress:progress('detecting',len(samples),len(samples));progress('assembling',None,None)
        with measured(profile,'assembly'):
            complete_settings=replace(settings,effective_roi=roi)
            pages=[Page(str(uuid4()),seg.representative_sample_id,'auto',seg.segment_id,
                        seg.segment_id,'auto') for seg in segments]
            project=Project(source,complete_settings,tuple(samples),transitions,segments,pages,
                            revision=0,cache_generation=cache_generation,
                            analysis_generation=str(uuid4()))
            result=AnalysisResult(project.samples,project.transitions,project.segments,
                                  project.analysis_generation)
        if profile is not None:profile.metadata['page_count']=len(pages)
        return project,result
    except BaseException:
        # Never discard or alter caches still owned by the previous Project.
        # Only this invocation's newly created, verified owner can be cleaned.
        if created_cache is not None:
            from .cache import _safe_owned_dir
            from shutil import rmtree
            import uuid
            candidate=Path(created_cache)
            expected=str(uuid.UUID(candidate.name.removeprefix('session-')))
            try:
                _safe_owned_dir(Path(cache_root).resolve(),candidate,expected)
            except (ValueError,OSError,RuntimeError):
                pass  # Fail closed rather than delete an uncertain directory.
            else:
                rmtree(candidate)
        raise


def requires_reanalysis(project:Project,settings:AnalysisSettings):
    return _settings_key(project.settings)!=_settings_key(settings)


def analyze_project(source,settings,cache_root,*,previous=None,cancel_token=None,
                    sampler=sample_stream,progress=None,profile=None,profile_path=None,decode_options=None):
    decode_options={'backend':'cpu-metadata','threads':0} if decode_options is None else decode_options
    profile=profile if profile is not None else (AnalysisProfile() if profile_path else None)
    if profile is not None:
        profile.metadata.update(decoder_backend=(decode_options or {}).get('backend','cpu'),
                                decoder_threads=(decode_options or {}).get('threads',0))
    try:
        with measured(profile,'total'):
            outcome=_analyze_project(source,settings,cache_root,previous=previous,
                cancel_token=cancel_token,sampler=sampler,progress=progress,profile=profile,decode_options=decode_options)
        if profile is not None:profile.metadata['status']='success'
        return outcome
    except BaseException as exc:
        if profile is not None:
            profile.metadata.update(status='failed',error_type=type(exc).__name__)
        raise
    finally:
        if profile_path is not None and profile is not None:
            try:
                profile.save(profile_path)
                print('Analysis profile saved:',profile_path,flush=True)
            except OSError as exc:
                print('Could not save analysis profile:',type(exc).__name__,flush=True)
