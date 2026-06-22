---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.model': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.ui': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-filtering': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-normalization': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.hash-column': patch
---

Migrate block onto the block-tools structurer with a full SDK upgrade
(@platforma-sdk/model & ui-vue 1.79.15, workflow-tengo 6.6.3, tengo-builder
4.0.9, block-tools 2.11.1). Adopts the canonical layout (oxlint/oxfmt, block
index, managed tsconfig/turbo/CI) and applies the author-code changes the bump
required: ag-grid 34, ReactiveFileContent instance API, PlNumberField, removal
of the dropped ui-vue `./styles` export, and workflow software-dependency
dedup. No block behaviour change; model remains V1.
