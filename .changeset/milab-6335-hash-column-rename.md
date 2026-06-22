---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.hash-column': patch
---

MILAB-6335: rename the hash-column software package from `@platforma-open/milaboratories.mixcr-clonotyping-2.hash-column` to the block's own namespace `@platforma-open/cellecta.drivermap-mixcr-clonotyping.hash-column` (matching the `vbc-*` packages). The package was a local copy that kept the scaffold's foreign name; the block now publishes its software artifact under its own name. The workflow's `importSoftware` reference is updated accordingly. No runtime behavior change.
