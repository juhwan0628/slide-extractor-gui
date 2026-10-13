# M8 correction — GOP-conditioned half with complete lazy edit index

2026-10-13. Status: complete in the corrected half-base scope. Implementation426502e plus covered final-review cache fixes.

## User direction restored

User22:24–22:29KST clarified that half was chosen to avoid roughly1fps-scale RGB/JPEG cost after
keyframe-only decoding. The assistant's all-only integration and half-editor exclusion were not an
approved policy change. That M8 completion was retracted; historical docs now mark the interpretation
superseded. Useful spatial detector/provenance/export safeguards remain.

Packet-only preflight chooseshalf for maximum key interval strictly<2s, including start/tail; >=2s
usesall. Native selection occurs before codec_send_packet, RGB conversion and JPEG. Unsupported
native codecs/configurations or unavailable helper restart clean CPUall and record actual policy.
NoFPS sampling or non-keyframe substitution. Helpers resolve env, bundled tools, source-build path.
Native Mac/Windows helper packaging remainsM10; current source worktree uses its built helper.

Prepared.samples = decoded observations; Prepared.keyframe_index = complete edit metadata.
Project.samples = complete edit index, with immutable observation membership in snapshots. Viewing
or manually selecting a skipped key does not expand detector observations; reanalysis keeps that
same half subset and cache generation. Legacy partial-half records do not falsely claim completeness.

Skipped previews are materialized at exact originalPTS by bounded GUI image worker; switch/close
cancels its resolver/decoder. Export materializes only selected uncached keys. Missing/corrupt
analysis images fail, never silently regenerate. Lazy writes require generated skipped filename in
the same observed-cache generation. Decoder remains keyframe-only for lazy/PDF paths.

Detailedv7 records effectivehalf input policy, complete-index flag and per-frame analysis-observed
flag. Boundary adjacency and segment membership refer to observations, while manual pages may use
any indexed keyframe. Strict oldv4/v5/v6 readers are preserved. Native profilethread=1 corrected.

## Evidence

RED: missingpacketindex API; spatialhalf all-forcing; missinglazyAPI; halfJSONrejection; GUI missing
skipped-image timeout; unsafe lazy cache target write; missing CPU decode profile forwarding.
GREEN: initial policy8; lazy/JSON48; GUI6; profile/models156; cancellation/strictfaults17.
Initial suite993passed128.22s exit0; after final-review fixes whole suite999passed132.68s exit0; package contracts43passed4.82s. No full native installed build.
Six real default-half cases exactly match frozen half research representative timestamps:

| Window | Full index | Initial analysis JPEGs | Automatic pages |
|---|---:|---:|---:|
| OriginalSP |301|151|3|
| Originalmulticore |301|151|4|
| Originalethics |304|152|6|
| Validation2SP |304|152|7|
| Validation2multicore |301|151|1|
| Validation2ethics |302|151|3|

Original3 also verified skipped preview, add/replace, exactPTS PDF/v7 exports and cache cleanup.
Results:Keyframe-M8-half-real-validation.json; script:scripts/verify_keyframe_half_m8.py.
These are mechanical/equivalence checks, not exhaustive source-frame recall. Validation2SP all
reference has11occurrences and fourcontent identities; half7contains threeidentities, with Notes
observations153/211/299 absent from half. Full index now exposes those skipped keys for manual
access, but this M8 does not automatically inspect/recover their image content. Do not infer that
half is universally content-equivalent or use this evidence as unapproved all-default authority.

## Final fresh review and fix evidence

Reviewer keyframe_half_correction_review: no Critical, two Important, no additional actionable Minor.
Lazy writes initially bypassed quota/reserve accounting and created unrecognized crash temporaries.
Reproduced free-disk reserve failure, stale manifest byte count, and unprunable partial temporary,
then extended the retained CachePin owner writer with original session/root/free limits, outstanding
reservation accounting under the existing budget lock, completed-manifest byte/heartbeat updates,
atomic JPEG publication and a narrowly recognized skipped temporary. Directory binding rejects a
foreign generation owner before writing. Five review tests plus that owner-binding regression were
RED→GREEN; focused cache/lazy/GUI35passed7.25s; full suite999passed132.68s exit0. Real six-case
half/equivalence/preview/edit/PDF verification rerun exit0 with the owned writer. No second review
was needed for these covering-test fixes. Reviewer also verified exact skipped JPEG equivalence
against CPUall for nonzero origin, rotations0/90/180/270 andSAR4/3. No Minor deferred.

## Decisions and costs

1. Explicit user correction supersedes prior all-only specs/completion; preserve safeguards and
   implement actual complete-index integration; cost larger correction than a default-only switch.
2. v7 extends full-index/observation metadata only where needed; retain old4/5/6; cost half detailed
   sidecar consumers must supportv7. PDF/simpleJSON unchanged.
3. Packet filter retains only key metadata in the shared disk-spooled process wrapper; no RGB during
   index; cost an extra demux preflight, reported separately in profiles.
4. Existing tests that deliberately replace synthetic sample arrays reset observation metadata,
   and partial-half fixtures explicitly mark incompleteindex; cost fixture edits, no weakened policy
   or duplicate/frame-integrity guards.
5. Reviewer did not judge installed package/device readiness, changed research thresholds or
   recovery of never-observed content: keep M9/M10 and separate quality work as their gates; cost
   installed behavior and automatic skipped-content recovery remain unverified/unimplemented here.

M9 repeated timings/quality accounting and M10 installed native packaging/release remain ahead.
Revisit identity remains user-deferred. No push/merge/release or extra human content labeling.

## Execution record

```text
# SDD ledger — plan: docs/milestones/Keyframe-M8-half-correction-plan.md
Base96cf359. User authorized half+GOP default restoration and complete-index/lazy editor.
Preflight: packetindex→preparation→fullProject/observation subset→GUI/lazy/export/JSON. Append fields to retain positional API.
Ruling: previous all-only specs/completion are superseded by explicit user correction — preserve useful implementation safeguards but restore half base — cost this correction requires new complete-index integration rather than a default-only switch.
Packet policy REDmissingmodule; threshold tests7GREEN; actualnativehalf JPEG/completeindex checks pass then REDallforce; full-index observation integration GREEN8. Lazy REDmissingAPI then schemaallforce; lazy/v7GREEN48 includingold4/5. GUI lazy REDtimeoutmissingimage then GREEN; synthetic80samplefixture now resets observation IDs. Puremodelmutatingfixture likewise resets IDs. Legacypartialhalf fixtures explicitly complete=False rather than inheritingall completionflag.
Ruling: schema7 extends complete-index/observed metadata only for completehalf/spatialhalf; retain existing4/5/6 exactvalidators — avoid conflating all edit entries with analysis observations — cost newhalf detailed sidecars requirev7 reader support.
Cachetarget REDoutsidegenerationwriteallowed; guard restricts skipped name and observed generation; GREEN. Firstsuite983pass1profilefailure; preserveCPUprofileforwarding REDmissingdecode_wait→GREEN. Profile native threadlabel corrected to1, packet-index cost measured.
Final implementation suite993passed128.22s exit0 /tmp/m8-half-final-suite.log; nativeGUI6passed; strictfaults17passed; profile/model156passed. Native real6cases exactfrozenhalf representatives; originalSP3/MC4/ethics6 with151/151/152initialJPEGs vs301/301/304fullindex. Preview+replace+pairedPDF/v7 passes onoriginal3; validation2 halfSP7/MC1/ethics3, matchingfrozenhalf; fullSP reference11. Known unobserved briefNotes remains automatic selection limitation, not policy change authority. No release/device claim.
Ruling: packetfilter keeps onlykeymetadata in shared disk-spooled process runner — avoids allpacket RAM and imagegeneration — cost an extra demuxpreflight measured in profile.
Ruling: fixtures replacing samplearrays reset observationmembership; legacyhalfpartial explicitly completenessFalse — match new model contract without weakening guard — cost fixture updates.
Implementation426502e clean; packagecontract43passed4.82s. Reviewdispatched freshkeyframe_half_correction_review, mostcapablemodel; no rereview scheduled for covering-test fixes.
Final review: noCritical; Importantlazybudgetbypass/stalemanifest and unrecognizedcrashlazytemp; noadditionalMinor. Fresh exactJPEGchecks origin/rotation0/90/180/270/SAR4/3 passed. Device/release/research-threshold/skipped-content-recovery notjudged.
Final: fixed budgets/accounting and crashcleanup — reserve/manifest/prune tests3RED; pinAPI originalsession/rootlimits2RED; foreignownerwrite1RED; ownedCachePin writer stores original limits, budget-lock reservation accounting, exactdirectory binding, completeManifestupdates, recognizedskippedtemporaries;35focusedGREEN7.25s; fullsuite999/999passed132.68s exit0.
Final: Ruling: reviewer declined device/release/research-threshold/unobservedcontentrecovery — keep M9/M10 and separatequality evidence as gates, not implicit policy reversal — cost installed behavior and automatic recovery remain unverified/unimplemented here.
Real6cases rerun aftercachefix exit0, original3/4/6halfcounts unchanged; pairedPDF/v7lazychecks successful. NoMinorDeferred. Branch/worktree preserved for M9/M10; no push/merge/release or repetitive permission menu.
```
