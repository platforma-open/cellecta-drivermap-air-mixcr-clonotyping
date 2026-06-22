import { ProgressPrefix } from "@platforma-open/cellecta.drivermap-mixcr-clonotyping.model";
import {
  AlignReport,
  AssembleReport,
  Qc,
} from "@platforma-open/milaboratories.mixcr-clonotyping-2.model";
import { isLiveLog, type AnyLogHandle } from "@platforma-sdk/model";
import { ReactiveFileContent } from "@platforma-sdk/ui-vue";
import { computed } from "vue";
import { useApp } from "./app";

const reactiveFileContent = ReactiveFileContent.useGlobal();

export type Result = {
  label: string;
  sampleId: string;
  progress: string;
  logHandle?: AnyLogHandle;
  alignReport?: AlignReport;
  assembleReport?: AssembleReport;
  qc?: Qc;
};

/** Relatively rarely changing part of the results */
export const resultMap = computed(() => {
  const app = useApp();

  const sampleLabels = app.model.outputs.sampleLabels;
  if (sampleLabels === undefined) return undefined;

  // Block-level run state: true until the whole workflow (MiXCR + clone export +
  // the VBC Python step) finishes — not just MiXCR.
  const blockRunning = app.model.outputs.isRunning;

  const resultMap = new Map<string, Result>();

  for (const sampleId in sampleLabels) {
    const label = sampleLabels[sampleId];
    const result: Result = {
      sampleId: sampleId,
      label: label,
      progress: blockRunning ? "Queued" : "Not started",
    };
    resultMap.set(sampleId, result);
  }

  // logs & reports

  const logs = app.model.outputs.logs;
  const qc = app.model.outputs.qc;
  const reports = app.model.outputs.reports;
  const progress = app.model.outputs.progress;
  // MiXCR log liveness per sample: the stream is live only while `mixcr analyze`
  // is still running for that sample.
  const mixcrLogLive = new Map<string, boolean>();
  if (logs) {
    for (const logData of logs.data) {
      const sampleId = logData.key[0] as string;
      const r = resultMap.get(sampleId);
      if (!r) continue;

      mixcrLogLive.set(sampleId, isLiveLog(logData.value));

      r.logHandle = logData.value;
    }
  }

  if (qc) {
    for (const qcData of qc.data) {
      const sampleId = qcData.key[0] as string;
      const r = resultMap.get(sampleId);
      if (!r || !qcData.value) continue;
      r.qc = reactiveFileContent.getContentJson(qcData.value.handle, Qc).value;
    }
  }

  if (reports)
    for (const report of reports.data) {
      const sampleId = report.key[0] as string;
      const reportId = report.key[1] as string;
      if (report.key[2] !== "json" || report.value === undefined) continue;
      const r = resultMap.get(sampleId);
      if (r) {
        switch (reportId) {
          case "align":
            // globally cached
            r.alignReport = reactiveFileContent.getContentJson(
              report.value.handle,
              AlignReport,
            )?.value;
            break;
          case "assemble":
            // globally cached
            r.assembleReport = reactiveFileContent.getContentJson(
              report.value.handle,
              AssembleReport,
            )?.value;
            break;
        }
      }
    }

  // Latest MiXCR progress line per sample (emitted only while its log is live).
  const mixcrProgress = new Map<string, string>();
  if (progress) {
    for (const progressData of progress.data) {
      const sampleId = progressData.key[0] as string;
      if (progressData.value) {
        mixcrProgress.set(sampleId, progressData.value.replace(ProgressPrefix, ""));
      }
    }
  }

  // Phase-aware status. MiXCR emits progress only while its log is live; once it
  // closes, clone export and the VBC Python step still run — tracked by the
  // block-level `isRunning`. Report "Done" only when the whole block has
  // finished, so the post-MiXCR phase shows "Processing clonotypes" instead of a
  // premature "Done".
  for (const r of resultMap.values()) {
    const logLive = mixcrLogLive.get(r.sampleId);
    if (logLive === undefined) {
      r.progress = blockRunning ? "Queued" : "Not started";
    } else if (logLive) {
      r.progress = mixcrProgress.get(r.sampleId) ?? "Running";
    } else {
      r.progress = blockRunning ? "Processing clonotypes" : "Done";
    }
  }

  return resultMap;
});
