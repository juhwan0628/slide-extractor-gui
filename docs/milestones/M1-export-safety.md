# M1 — export safety stabilization

## Approved scope

Resolve audit F1/F2/F8/F9 for the existing PDF-only and PDF+JSON export paths.
Keep source videos, unrelated files, overwrite consent, paired rollback and
explicit interrupted-export recovery protected. No algorithm, UI layout,
version, release or signing changes.

## Design and decisions

- Both modes and recovery use one canonical PDF resource lease. On macOS,
  conservatively normalize case and Unicode because default volumes alias them.
  Case-sensitive macOS volumes may serialize distinct aliases unnecessarily.
- A per-transaction activity lease spans PREPARED through commit. Recovery skips
  live jobs and reclaims abandoned jobs after ownership is released or a process
  exits. Low-level callers must close abandoned prepared transactions.
- Successful exports clean their own journal with their own validator rather than
  scanning other transactions. A job refused before publication removes only its
  verified staged files and unchanged PREPARED journal.
- Hardlink support is probed before frame rendering or changing user outputs.
  Unsupported paired export gives PDF-only/local-folder guidance; exclusive
  publication is not replaced by a weaker overwrite fallback.
- Once a PDF or pair is published, later verification/durability/cleanup failure
  carries committed outputs and a GUI warning. Cancellation cannot conceal it.

## Tests

Regression tests use synthetic media fixtures but real PDF rendering, journal
publication and leases. Frame extraction is stubbed only where video decoding
is irrelevant. Additional subprocess tests exercise cross-mode exclusion and
live-preparation recovery. Existing subprocess crash/rollback tests are retained.

Initial RED: eight original audit/GUI checks failed for the intended defects.
Additional RED: busy-job journal cleanup, post-publication lock/pair cleanup
status and macOS alias lock checks also exposed missing behavior.
Existing recovery tests now explicitly abandon live preparation before simulating
recovery; their target/stage/hash safety assertions remain unchanged.

Run with:
`QT_QPA_PLATFORM=offscreen python -m pytest`

Physical Windows/macOS reinstall and FAT/exFAT device verification belong to M5.
Different app versions running concurrently are outside this version's lease
protocol guarantee. Paid signing remains intentionally omitted.

## Verification

- Final full suite: 670 passed in 70.37s (Qt offscreen, Linux ARM).
- M1 regressions: 15 passed, including independent-process exclusion/recovery.
- Normal real-PDF roundtrip, PDF-only overwrite, source/JSON preservation and
  completed output-lock cleanup: passed.
- Independent review: one Important addressed with two RED→GREEN reproductions;
  one diagnostic Minor recorded below for M4.
- No native installer rebuild or release publication at this milestone.

Independent review identified one Important issue in the new caller cleanup:
closing a committed transaction recursively removed backups after verified
recovery refused changed output/unknown stage entries. Two new reproductions
failed; close now only releases ownership. Only verified recovery removes a
committed stage. Both regression cases pass.

Deferred Minor (M4 diagnostics): recovery currently skips all LeaseBusy activity
acquisition failures, including unsafe/unavailable lock files, as if a job were
live. Files remain protected, but the obstruction message can be more precise.
