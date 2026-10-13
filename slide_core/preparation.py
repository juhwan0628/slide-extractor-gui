"""Settings-independent, owned JPEG samples prepared before analysis."""
from dataclasses import dataclass,field
from pathlib import Path
from uuid import uuid4
from .media import probe_source,source_matches,MediaError
from .pts import keyframe_stream
from .config import KEYFRAME_ALGORITHM
from .cache import discard_cache,CacheCleanupError

@dataclass(frozen=True)
class PreparedSamples:
    source:object
    samples:tuple
    directory:Path
    cache_root:Path
    cache_generation:str
    cache_pin:object=field(repr=False,compare=False)

    sampling_algorithm:str=KEYFRAME_ALGORITHM

    def discard(self):
        if self.cache_pin is not None:self.cache_pin.close()
        if not discard_cache(self.cache_root,self.directory) and self.directory.exists():
            raise CacheCleanupError(f'Unable to remove sample cache: {self.directory}')


def prepare_samples(source,cache_root,*,cancel_token=None,progress=None):
    if cancel_token is not None:cancel_token.raise_if_cancelled()
    source=probe_source(Path(source),cancel_token=cancel_token) if not hasattr(source,'fingerprint') else source
    if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
    pins=[];directory=None
    try:
        common=dict(cancelled=cancel_token,progress=progress,cache_owner=pins.append)
        samples,directory=keyframe_stream(source,Path(cache_root),**common)
        if cancel_token is not None:cancel_token.raise_if_cancelled()
        if not source_matches(source):raise MediaError('SourceChanged',code='SourceChanged')
        return PreparedSamples(source,tuple(samples),directory,Path(cache_root),str(uuid4()),pins[0])
    except BaseException:
        for pin in pins:pin.close()
        if directory is not None and not discard_cache(cache_root,directory) and directory.exists():
            raise CacheCleanupError(f'Unable to remove sample cache: {directory}')
        raise
