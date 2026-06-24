---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.model': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.ui': patch
---

MILAB-6335: show an error state in the per-sample results table when the block fails.

The per-sample status derived "Done" purely from `isRunning` becoming false, but
`isRunning` (`getIsReadyOrError() === false`) goes false on **both** success and failure —
so a clone-export or VBC Python-step failure after MiXCR succeeded showed a green "Done"
instead of surfacing the failure (the very phase MILAB-6335 set out to make visible). The
model now exposes an `isErrored` output (true when any settled workflow output is in error)
and the results table reports "Error" for those samples instead of "Done".
