"""Settings-independent, owned JPEG samples prepared before analysis."""
from dataclasses import dataclass,field
from fractions import Fraction
from pathlib import Path
from uuid import uuid4
from .media import probe_source,source_matches,MediaError
from .pts import sample_stream
from .cache import discard_cache,CacheCleanupError

@dataclass(frozen=True)
class PreparedSamples:
    source:object
    fps:float
    samples:tuple
    directory:Path
    cache_root:Path
    cache_generation:str
    cache_pin:object=field(repr=False,compare=False)

    def discard(self):
        if self.cache_pin is not None:self.cache_pin.close()
        if not discard_cache(self.cache_root,self.directory) and self.directory.exists():
            raise CacheCleanupError(f'Unable to remove sample cache: {self.directory}')


def prepare_samples(source,cache_root,*,fps=.5,cancel_token=None,progress=None):
    if cancel_token is not None:cancel_token.raise_if_cancelled()
    source=probe_source(Path(source),cancel_token=cancel_token) if not hasattr(source,'fingerprint') else source
    if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
    pins=[];directory=None
    try:
        samples,directory=sample_stream(source,Path(cache_root),fps=Fraction(str(fps)),
            cancelled=cancel_token,progress=progress,cache_owner=pins.append,
            decode_options={'backend':'cpu-metadata','threads':0})
        if cancel_token is not None:cancel_token.raise_if_cancelled()
        if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
        return PreparedSamples(source,float(fps),tuple(samples),directory,Path(cache_root),str(uuid4()),pins[0])
    except BaseException:
        for pin in pins:pin.close()
        if directory is not None and not discard_cache(cache_root,directory) and directory.exists():
            raise CacheCleanupError(f'Unable to remove sample cache: {directory}')
        raise


def compact_samples(prepared,*,fps=.5):
    """Consume an exclusively owned complete cache, retaining bucket-first PTS."""
    from dataclasses import replace
    import json,os,time
    from .cache import _safe_owned_dir,_budget_lock
    if prepared.fps!=1 or fps!=.5:raise ValueError('Only 1 to 0.5 FPS compaction is supported')
    if not source_matches(prepared.source):raise MediaError('SourceChanged',code='SourceChanged')
    kept=[];seen=set()
    for sample in prepared.samples:
        bucket=int(sample.actual_time//2)
        if bucket not in seen:
            seen.add(bucket)
            kept.append(replace(sample,grid_index=bucket,nominal_time=Fraction(bucket*2)))
    if not kept:raise ValueError('Empty prepared cache')
    directory=prepared.directory
    with _budget_lock(prepared.cache_root):
        manifest=_safe_owned_dir(prepared.cache_root,directory)
        if not manifest['complete']:raise ValueError('Incomplete prepared cache')
        paths={Path(s.cache_path) for s in kept}
        for path in paths:
            if path.parent!=directory or not path.is_file() or path.is_symlink():
                raise ValueError('Invalid sample cache path')
        for path in directory.glob('*.jpg'):
            if path not in paths:path.unlink()
        manifest.update(bytes=sum(p.stat().st_size for p in paths),updated_at=time.time())
        temp=directory/'manifest.tmp'
        try:
            with temp.open('x',encoding='utf-8') as stream:json.dump(manifest,stream,sort_keys=True)
            os.replace(temp,directory/'manifest.json')
        finally:temp.unlink(missing_ok=True)
    return replace(prepared,fps=float(fps),samples=tuple(kept),cache_generation=str(uuid4()))
