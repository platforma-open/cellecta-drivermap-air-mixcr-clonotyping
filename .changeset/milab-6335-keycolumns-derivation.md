---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow': patch
---

MILAB-6335: derive the clonotype keyColumns from a single source of truth.

The full-length preset maintained `keyColumns` as a hand-edited list parallel to `features`,
so a future edit to one but not the other could silently produce a `clonotypeKey` that no
longer matches the export. `keyColumns` is now derived from each preset's `keyFeatures`
(emitted as `nSeq<Feature>`) plus `keyGeneColumns`, with an assertion that every `keyFeature`
is actually exported and a test pinning the derived result per preset. No behaviour change —
the derived lists are byte-identical to the previous hardcoded ones. Also clarifies the
`agg-clones` `rankingColumn` comment: `readCount` is a deliberate, never-NA selector of which
clone's display metadata represents a key, and the cross-sample sequencing-depth trade-off is
now documented.
