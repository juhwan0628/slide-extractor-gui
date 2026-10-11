# M4 — timing, distribution and diagnostic cleanup

## Approved scope

Audit F7/F11/F12 and the M1 deferred activity-lock diagnostic.
Preserve algorithms, user settings, unsigned beta policy and exact candidate
approval gates. No version bump, native rebuild, installer or release publication.

## Changes

- Background preparation records its complete wall time and publishes a local
  preparation-UUID diagnostic before ready, including failures before Analyze.
- Analyze profiles remaining preparation_wait, detector pipeline total, and
  click_to_result_total from the UI click timestamp. preparation_total already
  overlaps UI time and is not additive. Cancelled inflight preparation has an
  elapsed snapshot; it is not falsely described as completed. Profiles expose
  exception types rather than messages or video paths. The detector shares one
  profile and the GUI wrapper saves it once, including early wait failures.
- Existing source evaluation ZIP and Windows personal build kit are retained
  because current developer/test paths still consume them. Both now contain
  LICENSE. A regression unpacks each archive and executes the real shared spec
  with path checks for all required data/scripts/binaries.
- Native input collection copies existing dedicated OpenSSL license and runtime
  notice originals. Review binds installed texts and their hashes to those
  originals, alongside observed OpenSSL3 runtime version and native-file hash.
  Arbitrary NumPy/Python Apache text is refused.
- License data is located only in supported PyInstaller layouts (licenses,
  _internal/licenses, Contents/Resources/licenses); ambiguity, symlinked paths,
  missing material or changed bytes fail validation.
- LeaseUnavailable remains a LeaseBusy subclass for existing safety guards, but
  recovery reports unavailable/unsafe paths and locking-system errors instead
  of skipping them as live ownership. Genuine contention still skips live jobs.
- Packaging docs describe current workflow, personal source evaluation and
  unsigned beta policy. Early LICENSE_AUDIT state is explicitly historical.
  Native build triggers include GUI/core and runtime-notice/input changes.
  Existing release approval records remain unchanged and do not approve M4.

## Verification and review

Nine initial RED cases demonstrated missing preparation timings/failure reports,
archive LICENSE inputs, missing dedicated evidence check and unsafe recovery
lease classification. A separate silent-failure case also failed before its fix.

Independent review found one Important installer-layout mismatch and one Minor
locking-system diagnostic. Both were addressed in one fix pass: four RED cases
for Windows/macOS layouts and ENOLCK/EIO now pass. Further safety checks refuse
ambiguous and symlinked license layouts. Existing live-export contention and
source/profile regression tests remain included.

No physical Windows/macOS test, new installer or new legal certification is
claimed. M5 must build and inspect new exact candidate bytes and refresh
version/commit/run/hash approvals. Current FFmpeg artifact restoration uses a
historical run with finite retention; build documentation records that constraint.

Final suite results are recorded below after completion.

## Final verification

- M4 regressions: 16 passed in 2.46s.
- Final full suite: 706 passed in 74.57s, Qt offscreen/Linux ARM, process exit0.
- Focused timing/packaging/native-input/storage set: 55 passed in 5.11s before the two additional layout-safety cases.
- Independent review findings addressed with four RED→GREEN cases; final full suite passed after the fix pass.
- git diff --check passed; no release or version files changed.
