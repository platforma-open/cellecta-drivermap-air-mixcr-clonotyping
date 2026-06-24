---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-filtering': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-normalization': patch
---

MILAB-6335: port the VBC filter/normalize scripts up to kitt-cellecta/AIR_VBC_filtering main — QC gate, barcode-hopping filter, improved KDE thresholding (Silverman bandwidth, >2-maxima split, valley-depth gate, VBC 1->2->3 reliability fallback, 20x-jump threshold correction; the threshold function is now total and never returns None), and floor/zero-drop/NA template estimation. Retains the block adaptation layer: explicit-file CLI, the kit's tagValueMIVBC molecule tag, templateEstimateFraction output, empty-input/QC-fail handling, and the downstream column schema (no readCount_BC pivot; readFraction recomputed). Fixes the `cannot unpack non-iterable NoneType` crash on degenerate VBC bins.
