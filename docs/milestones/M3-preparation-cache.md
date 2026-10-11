# M3 — preparation retry and cache cleanup

## Approved scope

Resolve audit F4/F6/F10: retry failed video preparation, reclaim interrupted
owned sample caches, and keep temporary lock deletion failures retryable.
Preserve cancellation draining, reader barriers, live writer/project pins,
source files, unknown cache contents and current decoding settings.

## Changes

- Analyze replaces an already-failed preparation rather than waiting on the same
  stored error. The existing predecessor completion barrier prevents overlapping
  decoders and still blocks successors when cache cleanup failed. Running and
  successfully completed preparations remain reusable.
- A verified UUID-owned session may contain the exact producer temporaries:
  ASCII numeric names of at least eight digits ending in .tmp, and manifest.tmp.
  They must be regular single-link files. Unknown names, directories, symlinks
  and linked temporaries remain refused. Active leases still prevent removal.
- Delete sample files under the session lease, release the lease handle before
  unlinking it for Windows compatibility, and retain manifest.json until that
  unlink succeeds. A transient lock deletion denial therefore retains ownership
  metadata and can be retried safely.

## Tests and limits

Original-code regressions: five failed, six passed. Real child processes exit
with code77 during numeric JPEG or manifest publication; expired sessions must
be reclaimed. Other cases exercise live ownership, foreign filenames, symlink
and hardlink refusal, lock-unlink denial followed by retry, and actual Qt Analyze
after a silent transient decoder failure.

Additional Qt tests cancel a running preparation then retry after decoder drain,
and confirm a cleanup error prevents a second decoder. Existing tests cover
successful-cache reuse, FPS compaction, rapid FPS replacement, reader draining,
source replacement, cancellation and final app-close cleanup.

Focused preparation/cache tests: 54 passed in 10.27s (Linux ARM, Qt offscreen).
Full-suite and independent review results are recorded below when complete.

Caches retain existing TTL/budget pruning policies; this change does not eagerly
delete every crashed session at startup. Without a valid ownership manifest,
cleanup continues to refuse deletion. A crash after final manifest unlink and
before directory removal may leave an empty directory without sample data or a
lease; no blanket deletion of unverified directories was added.

Physical Windows/macOS installer validation remains M5. No version, installer or
release update is part of M3.

## Final verification

- Full suite: 690 passed in 73.09s; process exit0.
- Independent read-only review: no Critical, Important or Minor findings.
- git diff --check: passed.
- Commit is local on the stabilization branch; no release publication.
