"""M5 PTS-exact paired PDF + validated JSON v3 export."""
from __future__ import annotations
from slide_core.version import VERSION
import hashlib,json,tempfile,shutil,uuid
from pathlib import Path
from datetime import datetime,timezone
from fractions import Fraction
from .models import make_export_snapshot,SlideImage
from .media import source_matches,MediaError
from .pts import extract_selected
from .pdf import write_slides_pdf,validate_slides_pdf
from .timeline_json import dumps,loads
from .export import snapshot_export,ExportTransaction,recover_export,OutputOverwriteRequired,RecoveryRequired
from .config import DetectorConfig

def _r(r):return dict(x=r.x,y=r.y,width=r.width,height=r.height)

def payload_v3(snap,pdf_path,pdf_sha,export_id):
    src=snap.source;meta=dict(src.metadata);sett=snap.settings
    settings=dict(sett) if isinstance(sett,tuple) else sett
    roi=settings.effective_roi if hasattr(settings,'effective_roi') else settings['effective_roi']
    masks=settings.masks if hasattr(settings,'masks') else settings['masks']
    config=settings.detector if hasattr(settings,'detector') else settings['detector']
    config=config or DetectorConfig()
    samples=list(snap.samples);sample_ids={s.sample_id:f's{i:06d}' for i,s in enumerate(samples)}
    boundaries={t.transition_id:f'b{i:06d}' for i,t in enumerate(snap.transitions)}
    segments={g.segment_id:f'g{i:06d}' for i,g in enumerate(snap.segments)}
    def tm(x):return round(float(x),9)
    def metric(scores,adjacent=False):
        value=dict(scores)
        prefix='adjacent_' if adjacent else ''
        return dict(global_mad=float(value.get(prefix+'global_mad',0)),
          max_tile_mad=float(value.get(prefix+'max_tile_mad',0)),
          changed_fraction=float(value.get(prefix+'changed_fraction',0)))
    rows=[]
    for page in snap.pages:
        sample=next(s for s in samples if s.sample_id==page.representative_sample_id)
        rows.append(dict(page_id=page.page_id,pdf_page=len(rows)+1,
            representative_sample_id=sample_ids[sample.sample_id],
            representative_timestamp_s=tm(sample.actual_time),
            origin=page.origin,origin_segment_id=segments.get(page.origin_segment_id),
            derived_segment_id=segments.get(page.derived_segment_id),
            last_edit='insert' if page.last_edit_kind in ('add','insert') else page.last_edit_kind))
    duration=round(float(meta['duration_s']),9)
    nav=[dict(page_id=p['page_id'],start_s=0 if i==0 else p['representative_timestamp_s'],
         end_s=rows[i+1]['representative_timestamp_s'] if i+1<len(rows) else duration,
         basis='representative_order',is_slide_boundary=False) for i,p in enumerate(rows)]
    return dict(schema_version=3,source=dict(basename=src.path.name,size_bytes=src.size_bytes,
         mtime_ns=src.mtime_ns,chunk_sha256=src.fingerprint,stream_index=src.stream_index,
         codec=str(meta['codec']),coded_width=src.width,coded_height=src.height,
         sar_num=src.transform.sample_aspect_ratio.numerator,sar_den=src.transform.sample_aspect_ratio.denominator,
         rotation_cw=src.transform.rotation,display_width=src.transform.display_width,
         display_height=src.transform.display_height,time_base_num=int(meta['time_base_num']),
         time_base_den=int(meta['time_base_den']),origin_pts=int(meta['origin_pts']),
         time_origin='first_display_frame'),
       duration_s=duration,duration_kind=meta['duration_kind'],
       sampling=dict(algorithm='bucket-first-v1',fps=float(settings.fps),cache_max_width=640,jpeg_quality=90),
       roi=_r(roi),ignore_masks=[_r(m) for m in masks],
       detector=dict(algorithm='masked-anchor-tile-v1',image_max_width=320,debounce_samples=2,
         global_mad=.005,tile_mad=.025,pixel_delta=20,changed_fraction=.0002,tile_size=20,tile_stride=10,
         min_tile_valid_fraction=.5,mask_dilation_px=1,keep_unconfirmed=True),
       samples=[dict(sample_id=sample_ids[s.sample_id],grid_index=s.grid_index,
          nominal_timestamp_s=tm(s.nominal_time),source_pts=s.source_pts,
          timestamp_s=tm(s.actual_time),cache_width=s.width,cache_height=s.height) for s in samples],
       detected_boundaries=[dict(boundary_id=boundaries[t.transition_id],
          left_sample_id=sample_ids[t.left_sample_id],right_sample_id=sample_ids[t.right_sample_id],
          lower_s=tm(t.lower_time),upper_s=tm(t.upper_time),observed_at_s=tm(t.observed_time),
          true_boundary_s=None,uncertainty_kind='sampling_and_detector',
          status=t.reason,persistence_samples=t.persistence_samples,
          adjacent_metrics=metric(t.scores,adjacent=True),anchor_metrics=metric(t.scores)) for t in snap.transitions],
       detected_segments=[dict(segment_id=segments[g.segment_id],start_s=tm(g.start_time),
          end_s=tm(g.end_time),first_sample_id=sample_ids[g.first_sample_id],
          last_sample_id=sample_ids[g.last_sample_id],
          auto_representative_sample_id=sample_ids[g.representative_sample_id],
          start_boundary_id=boundaries.get(g.start_boundary_id)) for g in snap.segments],
       pages=rows,navigation_ranges=nav,
       artifact=dict(export_id=export_id,project_revision=snap.revision,
          created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
          generator_version=VERSION,pdf_basename=Path(pdf_path).name,
          pdf_page_count=len(rows),pdf_sha256=pdf_sha))

def export_project(project,destination,*,overwrite=False,sidecar_format='detailed',cancel_token=None,progress=None,snapshot=None):
    if sidecar_format not in ('detailed','simple'):raise ValueError('Unsupported JSON format')
    project.validate()
    if not project.pages:raise ValueError('Select at least one page')
    if not source_matches(project.source):raise MediaError('SourceChanged',code='SourceChanged')
    # The displayed analysis must still have usable, complete cache images.
    # Export frames themselves always come from the original video, never JPEG.
    from PIL import Image,UnidentifiedImageError
    referenced={page.representative_sample_id for page in project.pages}
    for sample in project.samples:
        if sample.sample_id not in referenced:continue
        cached=Path(sample.cache_path)
        if cached.is_symlink() or not cached.is_file():
            raise MediaError('CacheUnavailable: representative image missing; reanalyze',code='CacheUnavailable')
        try:
            with Image.open(cached) as image:
                if image.size != (sample.width,sample.height):
                    raise ValueError('Cached image shape mismatch')
                image.verify()
        except (OSError,ValueError,UnidentifiedImageError) as exc:
            raise MediaError('CacheUnavailable: corrupt representative image; reanalyze',
                             code='CacheUnavailable') from exc
    destination=Path(destination).with_suffix('.pdf')
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Recovery is explicit user action; never silently rollback another export.
    if list(destination.parent.glob('.slide-export-*.journal.json')):
        raise RecoveryRequired('Unfinished export in folder: '+str(destination.parent))
    paths=snapshot_export(project.source.path,destination,overwrite=overwrite)
    if snapshot is not None:
        if paths.paths!=snapshot.paths or paths.states!=snapshot.states:
            raise OutputOverwriteRequired('Output paths changed after approval; approve the current files')
        paths=snapshot
    snap=make_export_snapshot(project)
    tx=ExportTransaction(snap.source.path,paths)
    temp=Path(tempfile.mkdtemp(prefix='.pts-render-',dir=destination.parent))
    try:
        requested={s.sample_id:s for s in snap.samples}
        selections=[requested[p.representative_sample_id] for p in snap.pages]
        roi=project.settings.effective_roi
        frames=extract_selected(snap.source,selections,temp,cancelled=cancel_token,roi=roi,progress=progress)
        if len(frames)!=len(snap.pages):raise ValueError('Frame extraction count mismatch')
        images=[SlideImage(p,float(s.actual_time)) for p,s in zip(frames,selections,strict=True)]
        pdf=temp/'staged.pdf'
        if progress:progress('writing',None,None)
        write_slides_pdf(images,pdf,export_id=tx.export_id,cancel_token=cancel_token)
        if progress:progress('verifying',None,None)
        validate_slides_pdf(pdf,images,export_id=tx.export_id)
        raw=pdf.read_bytes()
        if sidecar_format=='detailed':
            payload=payload_v3(snap,destination,hashlib.sha256(raw).hexdigest(),tx.export_id)
            sidecar=dumps(payload).encode('utf-8')
            loads(sidecar,pdf_bytes=raw,pdf_page_count=len(images),pdf_export_id=tx.export_id)
        else:
            from .simple_json import encode_simple
            sidecar=encode_simple(project)
        def validate_pair(pdf_path,json_path):
            p=Path(pdf_path).read_bytes()
            validate_slides_pdf(pdf_path,images,export_id=tx.export_id)
            if sidecar_format=='detailed':
                loads(Path(json_path).read_bytes(),pdf_bytes=p,
                      pdf_page_count=len(images),pdf_export_id=tx.export_id)
            else:
                from .simple_json import encode_simple
                if Path(json_path).read_bytes()!=sidecar:
                    raise ValueError('Simple JSON changed during publication')
        tx.validator=validate_pair
        if cancel_token is not None:cancel_token.raise_if_cancelled()
        if not source_matches(snap.source):raise MediaError('SourceChanged',code='SourceChanged')
        if project.revision != snap.revision or project.analysis_generation!=snap.analysis_generation:
            raise RuntimeError('Project changed during export')
        if progress:progress('publishing',None,None)
        tx.prepare(raw,sidecar)
        tx.commit()
        recover_export(destination.parent,validator=validate_pair)
        if cancel_token is not None:cancel_token.mark_committed()
        return paths.paths
    finally:
        if not tx._prepared and not tx.journal_path.exists():
            tx._remove_stage()
        shutil.rmtree(temp,ignore_errors=True)
