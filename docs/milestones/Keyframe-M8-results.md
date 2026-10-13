# M8 — Complete production keyframe editing and explicit policy

> Superseded policy interpretation: user22:24–22:29KST clarified GOP-conditioned half is the product base. Prior all-forcing/half-editor exclusion and M8 completion were unauthorized assistant interpretation. See Keyframe-M8-half-correction-plan.md/results.md for current policy and implementation. Historical test evidence below remains a record, not authority for all default.

2026-10-13. Status: complete in the revised all-only product scope. Fresh review and covered export-guard fix complete.

## Result

- PreparedSamples validates effective all/half and cpu-keyframes/native-idr provenance.
- Project and immutable ExportSnapshot carry explicit provenance. Reanalysis retains exact sample
  tuple/cache generation; mismatched previous/prepared policies fail SelectionPolicyMismatch without
  modifying either cache/project. Spatial still requires all; half remains research-only.
- Project.keyframe_index exposes the complete production all timeline. Add/replace on a partial
  experimental half timeline fails FullKeyframesRequired. Existing all GUI timeline exposes every
  prepared keyframe; no second packet index, lazy decoding or new half UI was introduced.
- Spatial and legacy-half detailed sidecars use strict v6 with sampling.selection_policy. Legacy
  all remains v4; exact old v4/v5 validators and round-trip compatibility preserved. GUI save label
  and package smoke version follow the same central helper. Simple JSON/PDF-only unchanged.
- Analysis profiles now report actual prepared/previous decoder backend, selection policy and reuse.

## Verification

Detector polish:946passed118.91s, including three ranking-pass cancellations closing staging and
preserving old project/cache. M8 RED:6provenance failures,4JSON failures,1partial-edit failure.
GREEN:170model/provenance,63JSON/GUI/export,19M8focused. Initial suite962passed122.70s, exit0. After the reviewed export-guard fix: final full suite972passed121.19s, exit0.
Native5minmulticore:301ffprobe key-packet PTS exactlymatch301product indices; automatic4pages.
Oddordinal3at3s was added/replaced; edited5pagePDF+v6allsidecar verified exact sourcePTS48123.
Reanalysis reuses identical sample tuple/cache generation; ownedcache cleanup succeeds. Script:
scripts/verify_keyframe_m8.py; results:Keyframe-M8-real-validation.json.
No new human content classification was needed; this verifies mechanical access/edit/export,
not a new recall claim. No installed-device timings, native package build or release were performed.

## Fresh review

Independent reviewer keyframe_m8_review checked9dd3d1f..61d3b73;54focusedtests passed4.70s.
No Critical. One Important: paired export stale-project guard omitted newly appended provenance.
Two render-change and eight after-output-lock policy/backend cases reproduced publication before
fix. Shared guard now compares selection_policy and decoder_backend;30focusedtests pass5.50s.
One Minor deferred: native prepared profile decoder_threads=0 although helper uses1. Backend,
policy and cache_reused are truthful; M9 will resolve thread provenance with measurement reporting.
Reviewer did not judge installed devices, packaging, release readiness or content recall; those
remain M9/M10 and the previously accepted detector evidence. No second review of covered fixes.

## Decisions made, in order, and costs

1. Half lazy-editor/index scope superseded while production uses all after brief-page omissions:
   reuse complete all sample index; cost no full-index editor for experimentalhalf projects.
2. Resume from authorized milestones and explicit user instruction without repetitive spec/plan
   approvals; cost revised all-only M8 interpretation documented for correction.
3. Add/replace on half fails rather than silently snapping to incomplete samples; cost experimental
   half editing requires preparing all.
4. New spatial sidecar v6, legacyall4 and old5read retained; cost external detailedJSON consumers
   need v6 support. PDF and simpleJSON consumers are unaffected.
5. Reviewer set installed devices/packaging/release/content recall aside: retain M9/M10 and prior
   accepted detector evidence as gates; cost installed behavior remains unverified until those stages.

## Next

M9: repeated full-lecture timings, quality/CPU/memory/disk accounting, installed Mac/Windows timing
where available. M10: pinned helper/FFmpeg native packaging and release validation. Revisit identity,
overview filtering and one-frame late-annotation ranking remain outside this integration.

## Execution record

```text
# SDD ledger — plan: docs/milestones/Keyframe-M8-plan.md
Native inline, user authorized resume M8, base pending detector-polish commit.
Pre-flight: Project provenance -> snapshot -> JSON/GUI; Prepared provenance -> analysis reuse/profile. No incompatible parameter order: append default fields.
Ruling: half lazy-editor/index scope superseded while production remains all after demonstrated brief-page omissions — reuse complete all sample index — cost: no complete-index editing for experimental half projects.
Ruling: proceed from existing authorized milestones and explicit request to resume, without repeated spec/plan approval — user requests minimal review work — cost: revised all-only M8 interpretation is documented for correction.
Task1: complete — f4c2e43, polish946passed118.91s, eachrankscanpriorcachecoverage. M8plan9dd3d1f.
Tasks2/3 in progress: policyRED6fail; model/reuse/profileGREEN170passed; JSONRED4fail includingmissingpolicy/oldversion; JSON/GUI/exportGREEN63passed. EditingpartialhalfRED1fail; completeoddkeyedit/exportGREEN; combinedM8focused19passed4.34s.
Ruling: add/replace on experimentalhalf fails FullKeyframesRequired instead of silently snapping to a partial index — half is not a production editor path — cost: experimentalhalf editing requires re-preparing all.
Ruling: new spatial exports use schema6; legacyall exports remain4; old5validation is unchanged — strictsamplingfield evolution — cost: external consumers must addv6 support for new detailed exports.
Real5minmulticore: ffprobe301keypackets exactlymatch301productindexPTS; nativeall, automatic4pages; add/replaceoddordinal3 at3s, PDF5pages+v6allsidecar verifiesPTS; reanalysis exacttuple/generation reuse; tempcache discarded. /tmp/m8-real.log, Keyframe-M8-real-validation.json.
Task2/3/4: complete —61d3b73; fullsuite962passed122.70s exit0; secondreal-script run alsoexit0 validatesrealnativeprofilebackend. Commit9dd3d1f..61d3b73 captures allchanges. Freshread-onlyM8review dispatched; no device/release work.
Final review: keyframe_m8_review9dd3d1f..61d3b73: noCritical; ImportantP2 appendedprovenanceomittedfrompairedexportguard; Minorpre-existingnativeprofilethread0vshelper1. Focusedreview54passed4.70s; nativeprofilereproactualhelper; no independentcontent/deviceclaim.
Final: fixed pending fullsuite — renderprovenancemutation2REDfail and publication-lockpolicy/backendchanges8REDfail; comparebothfields in shared pairedexportguard; focused30GREEN5.50s. Entire finalsuite running /tmp/m8-final-suite.log.
Final: minor (deferred): native prepared profile reports decoder_threads=0 although helper uses1; backend/policy/reuse are correct; correct thread provenance with M9 measurements.
Final: fixed exportprovenanceguard — test_changed_provenance_during_render_does_not_publish and test_publication_guard_rechecks_after_output_lock_before_any_output_changes policy/backend parameters10RED→GREEN; finalfullsuite972/972passed121.19s exit0.
Final: Ruling: reviewer declined installed devices/packaging/release/content recall — keep M9/M10 and accepted detector evidence as the gates; M8 only mechanical policy/edit/export validation — cost installed behavior remains unverified until those stages.
Finish: preserve feature/keyframe-0.5 existing worktree for M9/M10; no push/merge/release. Existing authorization is continued development, not branch integration; no redundant option menu.
```
