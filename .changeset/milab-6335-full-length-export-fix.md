---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow': patch
---

MILAB-6335: fix Full-Length Profiling crash (`column nSeqVDJRegion does not exist in export`).

The full-length preset export config declared `VDJRegion` / `nSeqVDJRegion`, but the kit
assembles clonotypes on `CDR1_TO_FR4` (`{CDR1Begin:FR4End}`). The key column is now
`nSeqCDR1_TO_FR4`, uncovered `FR1` is dropped, and V-segment mutations start at `CDR1Begin`.
