"""Silent preparation; one producer is shared by early and late Analyze clicks."""
from threading import Event,Thread,Lock
from time import perf_counter
from slide_core.preparation import prepare_samples,compact_samples
from slide_core.models import CancelToken,CancelledError
from slide_core.cache import CacheCleanupError

class BackgroundSamples:
    def __init__(self,source,cache_root,*,fps=.5,predecessor=None,release_readers=None,profile_path=None):
        self.started_at=perf_counter();self.finished_at=None;self.profile_path=profile_path
        self.source=source;self.fps=fps
        self.token=CancelToken();self.ready=Event();self.done=Event();self._dispose=Event()
        self.result=None;self.error=None;self.adopted=False
        self._lock=Lock();self._handoff=None;self.cleanup_error=None
        self._release_readers=release_readers
        self._incoming=None
        if predecessor is not None:
            with predecessor._lock:
                if (predecessor.ready.is_set() and not predecessor.token.cancelled
                        and predecessor.result is not None and not predecessor.adopted
                        and predecessor.source==source and predecessor.fps==1 and fps==.5):
                    self._incoming=predecessor.result
                    predecessor._handoff=self._incoming
                predecessor.close()
        self._thread=Thread(target=self._run,args=(cache_root,predecessor),daemon=True,
                            name='slide-sample-preparation')
        self._thread.start()

    def _run(self,cache_root,predecessor):
        try:
            if predecessor is not None:
                # Drain the entire cancellation chain before another decoder starts.
                predecessor.done.wait()
                predecessor._handoff=None
                self.cleanup_error=predecessor.cleanup_error
                if self.cleanup_error is not None:raise self.cleanup_error
            self.token.raise_if_cancelled()
            if self._incoming is not None:
                self.result=compact_samples(self._incoming,fps=self.fps)
                self._incoming=None
            else:
                self.result=prepare_samples(self.source,cache_root,fps=self.fps,cancel_token=self.token)
        except BaseException as exc:
            self.error=exc
            self.cleanup_error=self.cleanup_error or (exc if isinstance(exc,CacheCleanupError) else getattr(exc,'cache_cleanup_error',None))
            if self.cleanup_error is not None:self.error=self.cleanup_error
            if self._incoming is not None:
                try:self._incoming.discard()
                except BaseException as cleanup:self.cleanup_error=cleanup
            self._incoming=None
        finally:
            self.finished_at=perf_counter()
            if self.profile_path is not None:
                from slide_core.profiling import AnalysisProfile
                profile=AnalysisProfile()
                profile.seconds['preparation_total']=self.finished_at-self.started_at
                profile.metadata.update(status='failed' if self.error is not None else 'success',
                    sample_fps=self.fps,timing_scope='Background preparation including predecessor drain; overlaps GUI idle time')
                if self.error is not None:profile.metadata['error_type']=type(self.error).__name__
                try:profile.save(self.profile_path)
                except OSError as exc:print('Could not save preparation profile:',type(exc).__name__,flush=True)
            self.ready.set()
        # Retain the writer lease until the GUI adopts or discards this cache.
        self._dispose.wait()
        try:
            if self._release_readers is not None:self._release_readers()
            if self.result is not None and not self.adopted and self._handoff is None:
                self.result.discard()
        except BaseException as exc:self.cleanup_error=exc
        finally:
            self.result=None;self.done.set()

    def wait(self,cancel_token):
        while not self.ready.wait(.05):
            if cancel_token is not None:cancel_token.raise_if_cancelled()
        if cancel_token is not None:cancel_token.raise_if_cancelled()
        if self.error is not None:raise self.error
        if self.token.cancelled or self.result is None:raise CancelledError('Preparation cancelled')
        return self.result

    def close(self):
        self.token.cancel();self._dispose.set()
