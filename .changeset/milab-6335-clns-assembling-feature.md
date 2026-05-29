---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow': patch
---

MILAB-6335: annotate the clns column with the preset's actual assembling feature instead of a hardcoded `"CDR3"`. Full-length clones (assembled on `CDR1_TO_FR4`) are now labeled correctly, so downstream blocks reading `mixcr.com/assemblingFeature` get the right value.
