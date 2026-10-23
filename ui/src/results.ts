import {
  AlignReport,
  AssembleReport,
  ProgressPrefix,
  Qc,
} from "@platforma-open/cellecta.drivermap-mixcr-clonotyping.model";
import type { AnyLogHandle } from "@platforma-sdk/model";
import { ReactiveFileContent } from "@platforma-sdk/ui-vue";
import { computed } from "vue";
import { useApp } from "./app";

const reactiveFileContent = ReactiveFileContent.useGlobal();

// MiXCR runs as one command per step. Step logs and progress arrive keyed by (sampleId, step).
// The workflow leads each step key with its zero-padded run position (`003:assemble`), so the
// keys sort in run order and the furthest step sorts last.

type Entries<T> = { key: unknown[]; value?: T }[];

/** One MiXCR step's log. `key` is the workflow's `003:assemble`; `label` reads `003 assemble`. */
export type StepLog = { key: string; label: string; handle: AnyLogHandle };

/** Each sample's step logs, in run order. */
function logsPerSample(entries: Entries<AnyLogHandle> | undefined): Map<string, StepLog[]> {
  const out = new Map<string, StepLog[]>();
  const ordered = [...(entries ?? [])].sort((a, b) =>
    String(a.key[1]).localeCompare(String(b.key[1])),
  );
  for (const e of ordered) {
    if (e.value === undefined) continue;
    const sampleId = e.key[0] as string;
    const key = String(e.key[1]);
    const logs = out.get(sampleId) ?? [];
    logs.push({ key, label: key.replace(":", " "), handle: e.value });
    out.set(sampleId, logs);
  }
  return out;
}

/** The value of the furthest step that has one, for each sample. */
function furthestStep<T>(entries: Entries<T> | undefined): Map<string, T> {
  const best = new Map<string, { step: string; value: T }>();
  for (const entry of entries ?? []) {
    if (entry.value === undefined) continue;
    const sampleId = entry.key[0] as string;
    const step = String(entry.key[1]);
    const current = best.get(sampleId);
    if (current !== undefined && step < current.step) continue;
    best.set(sampleId, { step, value: entry.value });
  }
  return new Map([...best].map(([sampleId, e]) => [sampleId, e.value]));
}

export type Result = {
  label: string;
  sampleId: string;
  progress: string;
  logs: StepLog[];
  alignReport?: AlignReport;
  assembleReport?: AssembleReport;
  qc?: Qc;
};

/** Relatively rarely changing part of the results */
export const resultMap = computed(() => {
  const app = useApp();

  const sampleLabels = app.model.outputs.sampleLabels;
  if (sampleLabels === undefined) return undefined;

  // Block-level run state: true until the whole workflow (MiXCR + clone export + the VBC
  // Python step) finishes — not just MiXCR.
  const blockRunning = app.model.outputs.isRunning;
  // Block-level error state: `blockRunning` goes false on both success and failure, so without
  // this a failed post-MiXCR step would show a green "Done".
  const blockErrored = app.model.outputs.clonotypingStatus?.ok === false;

  const resultMap = new Map<string, Result>();
  for (const sampleId in sampleLabels) {
    resultMap.set(sampleId, {
      sampleId,
      label: sampleLabels[sampleId],
      progress: blockRunning ? "Queued" : "Not started",
      logs: [],
    });
  }

  for (const [sampleId, logs] of logsPerSample(app.model.outputs.logs?.data)) {
    const r = resultMap.get(sampleId);
    if (r) r.logs = logs;
  }

  // The qc result is the last thing MiXCR writes for a sample.
  const mixcrDone = new Set<string>();
  const qc = app.model.outputs.qc;
  if (qc) {
    for (const qcData of qc.data) {
      const sampleId = qcData.key[0] as string;
      const r = resultMap.get(sampleId);
      if (!r || !qcData.value) continue;
      mixcrDone.add(sampleId);
      r.qc = reactiveFileContent.getContentJson(qcData.value.handle, Qc).value;
    }
  }

  const reports = app.model.outputs.reports;
  if (reports)
    for (const report of reports.data) {
      const sampleId = report.key[0] as string;
      const reportId = report.key[1] as string;
      if (report.key[2] !== "json" || report.value === undefined) continue;
      const r = resultMap.get(sampleId);
      if (r) {
        switch (reportId) {
          case "align":
            r.alignReport = reactiveFileContent.getContentJson(
              report.value.handle,
              AlignReport,
            )?.value;
            break;
          case "assemble":
            r.assembleReport = reactiveFileContent.getContentJson(
              report.value.handle,
              AssembleReport,
            )?.value;
            break;
        }
      }
    }

  // A step whose stdout carries no progress line yet reports a blank line; the last step
  // that did report one stands until the next one speaks.
  const reported = (app.model.outputs.progress?.data ?? []).filter(
    (e) => e.value !== undefined && e.value.replace(ProgressPrefix, "").trim().length > 0,
  );
  const mixcrProgress = furthestStep(reported);

  // Phase-aware status. Once MiXCR has written a sample's qc result, clone export and the VBC
  // Python step still run — tracked block-wide by `isRunning`, since the by-clone-key
  // aggregation spans all samples. So a sample is:
  //   - its furthest MiXCR step's progress while MiXCR runs on it,
  //   - "Error" once the block has settled into a failure,
  //   - "Processing clonotypes" while the block is still running past MiXCR,
  //   - "Done" only when the whole block has finished successfully.
  for (const r of resultMap.values()) {
    if (blockErrored && (r.logs.length > 0 || mixcrDone.has(r.sampleId))) {
      r.progress = "Error";
    } else if (!mixcrDone.has(r.sampleId)) {
      if (r.logs.length === 0) r.progress = blockRunning ? "Queued" : "Not started";
      else r.progress = mixcrProgress.get(r.sampleId)?.replace(ProgressPrefix, "") ?? "Running";
    } else {
      r.progress = blockRunning ? "Processing clonotypes" : "Done";
    }
  }

  return resultMap;
});
