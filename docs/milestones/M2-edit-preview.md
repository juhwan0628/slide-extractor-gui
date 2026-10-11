# M2 — editing and preview stabilization

## Approved scope

Resolve audit F3 (Replace modifies an unselected focused page) and F5 (rapid
scrubbing loses the final preview). Preserve multi-selection, Merge/Delete,
Undo/Redo and existing memory limits. No layout, detection algorithm, version,
installer or release changes.

## Changes

- Replace resolves its target from the sole selected page ID. The command itself
  rejects empty/multiple selections and non-edit states, including direct calls.
  Existing history snapshots retain selection, focus, range and sample index.
- Visible preview requests promote already-prefetched entries or displace the
  last queued background entry when full, then run before older pending work.
  The pending queue remains limited to 16; detached delivery remains limited to
  eight. An active disk read finishes normally and generation guards still apply.
- Thumbnail cursor retries after any successful image delivery, so displacement
  cannot permanently stop thumbnail loading after scrubbing ends.
- While awaiting a new preview, clear the previous resize image as well as the
  displayed pixmap to prevent stale repaint on resize.

## Verification

- Five actual offscreen Qt regressions failed against the original HEAD for the
  intended selection, command-guard and final-preview defects after correcting
  synthetic fixture field names and UUIDs.
- Focused tests: 11 passed in 0.99s. Actual Ctrl-click gestures reproduce selected
  A/current B; Replace updates A, Undo restores original selection/focus/frame
  index and Redo reapplies the same edit. Zero/multiple selections and export
  state reject direct Replace.
- A blocked QImage read plus 80 seeks verifies final frame pixels, bounded queue
  and complete page thumbnails. Loader tests verify promotion without duplicate
  entries, latest-visible service order and stale inflight generation discard.
- Full suite: 677 passed in 71.14s, Linux ARM with Qt offscreen, including existing
  Merge/Delete/history, packaged smoke and M1 storage regressions.
- git diff --check passed. Independent read-only review found no Critical,
  Important or Minor issues.
- Physical macOS/Windows installer verification remains M5; no installer was
  rebuilt or release published during M2.
