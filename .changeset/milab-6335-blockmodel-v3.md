---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.model': minor
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.ui': minor
'@platforma-open/cellecta.drivermap-mixcr-clonotyping': minor
---

MILAB-6335: migrate the block model from V1 (`BlockModel.create()`) to `BlockModelV3`.

The model now holds a unified `BlockData` (`DataModelBuilder`) with a `.upgradeLegacy` step that maps the V1 `{ args, uiState }` split onto it, so persisted V1 projects upgrade transparently. The block title (formerly V1 `uiState.title`) is UI-only and stripped in `.args`; the workflow args (`input`, `preset`, `limitInput`, `chains`) are projected unchanged. No `prerunArgs` — the workflow has no prerun phase, so it falls back to `args`. UI bindings move from `app.model.args.*` / `app.model.ui.*` to `app.model.data.*`, and the UI entry switches `defineApp` → `defineAppV3`. No change to block behavior, outputs, or the workflow.
