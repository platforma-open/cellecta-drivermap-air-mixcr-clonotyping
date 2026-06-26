---
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow": patch
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.model": patch
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.ui": patch
---

MILAB-6335: surface a failed VBC Python step instead of a false-green "Done".

When `mixcr analyze` succeeded but the downstream VBC filtering/normalization step
failed (per sample), the results table still showed every sample as "Done". The
per-sample VBC errors are buried inside the `clones` exportFrame, where `getError()`
on the frame's binary-partitioned columns cannot reach them, so the model could not
detect the failure.

The workflow now also emits `vbcStatus` — a nested ResourceMap (`[chain]` ->
per-sample `cloneTableTsv`) carrying each chain's VBC result before XSV import, so a
failed sample's resource is reachable in an error state. The model replaces the
bespoke `isErrored` boolean with an idiomatic `clonotypingStatus` `OutputWithStatus`
envelope: it walks both levels of `vbcStatus` (via `parseResourceMap`) and scans every
top-level output field, and reports `ok: false` once the run has settled into a failure
(MiXCR analyze/export error, or a VBC-step error). `isRunning` is unchanged.

The UI consumes the envelope: the per-sample results rows show "Error" instead of a
false-green "Done".
