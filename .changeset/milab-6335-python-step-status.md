---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.ui': patch
---

MILAB-6335: stop showing a premature "Done" during the post-MiXCR phase.

Per-sample status is now phase-aware. While `mixcr analyze` runs it shows MiXCR progress (as before); once MiXCR finishes for a sample but clone export and the VBC Python step are still running (tracked by the block-level `isRunning`), it shows "Processing clonotypes"; "Done" appears only when the whole block has finished. Also fixes a pre-existing quirk where MiXCR-log liveness was computed once globally and applied to every sample.
