---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.ui': patch
---

MILAB-6335: open the Settings panel automatically when the block has no input selected yet (fresh add), so the user is prompted to configure it. Driven by initializing the local `settingsOpen` state from `app.model.data.input === undefined` at setup — no model change, no reactive write-back.
