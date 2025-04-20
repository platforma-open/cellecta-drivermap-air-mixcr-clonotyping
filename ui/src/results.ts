import { ProgressPrefix } from '@platforma-open/cellecta.drivermap-mixcr-clonotyping.model';
import {
  AlignReport,
  AssembleReport,
  Qc,
} from '@platforma-open/milaboratories.mixcr-clonotyping-2.model';
import { isLiveLog, type AnyLogHandle } from '@platforma-sdk/model';
import { ReactiveFileContent } from '@platforma-sdk/ui-vue';
import { computed } from 'vue';
import { useApp } from './app';

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

  const resultMap = new Map<string, Result>();

  for (const sampleId in sampleLabels) {
    const label = sampleLabels[sampleId];
    const result: Result = {
      sampleId: sampleId,
      label: label,
      progress: app.model.outputs.isRunning ? 'Queued' : 'Not started',
    };
    resultMap.set(sampleId, result);
  }

  // logs & reports

  const logs = app.model.outputs.logs;
  const qc = app.model.outputs.qc;
  const reports = app.model.outputs.reports;
  const progress = app.model.outputs.progress;
  let done = false;
  if (logs) {
    for (const logData of logs.data) {
      const sampleId = logData.key[0] as string;
      const r = resultMap.get(sampleId);
      if (!r) continue;

      done = !isLiveLog(logData.value);

      r.logHandle = logData.value;
    }
  }

  if (qc) {
    for (const qcData of qc.data) {
      const sampleId = qcData.key[0] as string;
      const r = resultMap.get(sampleId);
      if (!r || !qcData.value) continue;
      r.qc = ReactiveFileContent.getContentJson(qcData.value.handle, Qc).value;
    }
  }

  if (reports)
    for (const report of reports.data) {
      const sampleId = report.key[0] as string;
      const reportId = report.key[1] as string;
      if (report.key[2] !== 'json' || report.value === undefined) continue;
      const r = resultMap.get(sampleId);
      if (r) {
        switch (reportId) {
          case 'align':
            // globally cached
            r.alignReport = ReactiveFileContent.getContentJson(
              report.value.handle,
              AlignReport,
            )?.value;
            break;
          case 'assemble':
            // globally cached
            r.assembleReport = ReactiveFileContent.getContentJson(
              report.value.handle,
              AssembleReport,
            )?.value;
            break;
        }
      }
    }

  if (progress) {
    for (const progressData of progress.data) {
      const sampleId = progressData.key[0] as string;
      const r = resultMap.get(sampleId);
      if (!r) continue;

      const p = done ? 'Done' : progressData.value?.replace(ProgressPrefix, '') ?? 'Not started';

      r.progress = p;
    }
  }

  return resultMap;
});
