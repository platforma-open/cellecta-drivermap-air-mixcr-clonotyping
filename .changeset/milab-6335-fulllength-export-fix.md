---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow': patch
---

MILAB-6335: fix Full-Length Profiling crash (`column nSeqVDJRegion does not exist in export`).

The `cellecta-human-rna-xcr-full-length-mivbc-drivermap-air-v2` preset assembles clones by `{CDR1Begin:FR4End}`, not VDJRegion, so MiXCR never exports an `nSeqVDJRegion` column. The preset entry's `keyColumns` referenced `nSeqVDJRegion` and `assemblingFeature` was `VDJRegion` — neither present among the entry's exported `features` — so `keyAxesSpec` panicked. The clone key now uses the consecutive regions spanning the assembling feature (`nSeqCDR1`, `nSeqFR2`, `nSeqCDR2`, `nSeqFR3`, `nSeqCDR3`, `nSeqFR4`) plus the V/J/C gene calls, and `assemblingFeature` (the default-visible aa-column anchor) is set to `CDR3`.
