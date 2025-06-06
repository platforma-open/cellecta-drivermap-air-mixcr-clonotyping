<script setup lang="ts">
import { AgGridVue } from 'ag-grid-vue3';

import type { Qc } from '@platforma-open/milaboratories.mixcr-clonotyping-2.model';
import type { PlAgHeaderComponentParams } from '@platforma-sdk/ui-vue';
import {
  AgGridTheme,
  PlAgCellStatusTag,
  PlAgChartStackedBarCell,
  PlAgOverlayLoading,
  PlAgOverlayNoRows,
  PlAgTextAndButtonCell,
  PlBlockPage,
  PlBtnGhost,
  PlMaskIcon24,
  PlSlideModal,
  autoSizeRowNumberColumn,
  createAgGridColDef,
  makeRowNumberColDef,
} from '@platforma-sdk/ui-vue';
import type { ColDef, GridApi, GridOptions, GridReadyEvent } from 'ag-grid-enterprise';
import { ClientSideRowModelModule, ModuleRegistry } from 'ag-grid-enterprise';
import { computed, reactive, shallowRef } from 'vue';
import { useApp } from '../app';
import { getAlignmentChartSettings } from '../charts/alignmentChartSettings';
import { getChainsChartSettings } from '../charts/chainsChartSettings';
import { parseProgressString } from '../parseProgress';
import { resultMap, type Result } from '../results';
import SampleReportPanel from './SampleReportPanel.vue';
import SettingsPanel from './SettingsPanel.vue';
// import SampleReportPanel from './SampleReportPanel.vue';
// import SettingsPanel from './SettingsPanel.vue';

const app = useApp();

const rows = computed(() => [...(resultMap.value?.values() ?? [])]);
const data = reactive<{
  settingsOpen: boolean;
  sampleReportOpen: boolean;
  selectedSample: string | undefined;
}>({
  settingsOpen: false,
  sampleReportOpen: false,
  selectedSample: undefined,
});

ModuleRegistry.registerModules([ClientSideRowModelModule]);

const gridApi = shallowRef<GridApi>();
const onGridReady = (params: GridReadyEvent) => {
  gridApi.value = params.api;
  autoSizeRowNumberColumn(params.api);
};

const defaultColumnDef: ColDef = {
  suppressHeaderMenuButton: true,
  lockPinned: true,
  sortable: false,
};

const qcPriority = { OK: 0, WARN: 1, ALERT: 2 };
const columnDefs: ColDef<Result>[] = [
  makeRowNumberColDef(),
  createAgGridColDef<Result, string>({
    colId: 'label',
    field: 'label',
    headerName: 'Sample',
    headerComponentParams: { type: 'Text' } satisfies PlAgHeaderComponentParams,
    pinned: 'left',
    lockPinned: true,
    sortable: true,
    cellRenderer: PlAgTextAndButtonCell,
    cellRendererParams: {
      invokeRowsOnDoubleClick: true,
    },
  }),
  createAgGridColDef<Result, string>({
    colId: 'progress',
    field: 'progress',
    headerName: 'Progress',
    headerComponentParams: { type: 'Progress' } satisfies PlAgHeaderComponentParams,
    progress(cellData, cd) {
      const parsed = parseProgressString(cellData);

      const p = cd?.data?.progress;
      if (p === 'Not started' || p === 'Queued') {
        return {
          status: 'not_started',
          text: parsed.stage,
        };
      }

      return {
        status: parsed.stage === 'Done' ? 'done' : 'running',
        percent: parsed.percentage,
        text: parsed.stage,
        suffix: parsed.etaLabel ?? '',
      };
    },
  }),
  createAgGridColDef({
    colId: 'qc',
    field: 'qc',
    width: 126,
    cellRendererSelector: (cellData) => {
      const type = (cellData.data?.qc as Result['qc'])?.reduce(
        (result: Qc[number]['status'], item) =>
          qcPriority[item.status] > qcPriority[result] ? item.status : result,
        'OK',
      );
      return {
        component: PlAgCellStatusTag,
        params: { type },
      };
    },
    headerName: 'Quality',
    headerComponentParams: { type: 'Text' } satisfies PlAgHeaderComponentParams,
    noGutters: true, // this means "no padding" i. e. --ag-cell-horizontal-padding: 0px & --ag-cell-vertical-padding: 0px
  }),
  createAgGridColDef<Result, string>({
    colId: 'alignmentStats',
    headerName: 'Alignments',
    headerComponentParams: { type: 'Text' } satisfies PlAgHeaderComponentParams,
    flex: 1,
    cellStyle: {
      '--ag-cell-horizontal-padding': '12px',
    },
    cellRendererSelector: (cellData) => {
      const value = getAlignmentChartSettings(cellData.data?.alignReport);
      return {
        component: PlAgChartStackedBarCell,
        params: { value },
      };
    },
  }),
  createAgGridColDef<Result, string>({
    colId: 'chainsStats',
    headerName: 'Chains',
    headerComponentParams: { type: 'Text' } satisfies PlAgHeaderComponentParams,
    flex: 1,
    cellStyle: {
      '--ag-cell-horizontal-padding': '12px',
      // '--ag-cell-horizontal-border': 'solid rgb(150, 150, 200);',
      // 'border-width': '0'
    },
    cellRendererSelector: (cellData) => {
      const value = getChainsChartSettings(cellData.data?.alignReport);
      return {
        component: PlAgChartStackedBarCell,
        params: { value },
      };
    },
  }),

];

const gridOptions: GridOptions<Result> = {
  getRowId: (row) => row.data.sampleId,
  onRowDoubleClicked: (e) => {
    data.selectedSample = e.data?.sampleId;
    data.sampleReportOpen = data.selectedSample !== undefined;
  },
  components: {
    PlAgTextAndButtonCell,
  },
};
</script>

<template>
  <PlBlockPage>
    <template #title>DriverMap™ AIR Clonotyping</template>
    <template #append>
      <PlBtnGhost @click.stop="() => (data.settingsOpen = true)">
        Settings
        <template #append>
          <PlMaskIcon24 name="settings" />
        </template>
      </PlBtnGhost>
    </template>
    <div :style="{ flex: 1 }">
      <AgGridVue
        :theme="AgGridTheme"
        :style="{ height: '100%' }"
        :rowData="rows"
        :defaultColDef="defaultColumnDef"
        :columnDefs="columnDefs"
        :grid-options="gridOptions"
        :loadingOverlayComponentParams="{ notReady: true }"
        :loadingOverlayComponent="PlAgOverlayLoading"
        :noRowsOverlayComponent="PlAgOverlayNoRows"
        @grid-ready="onGridReady"
      />
    </div>
  </PlBlockPage>
  <PlSlideModal
    v-model="data.settingsOpen"
    :shadow="true"
    :close-on-outside-click="true"
  >
    <template #title>Settings</template>
    <SettingsPanel />
  </PlSlideModal>
  <PlSlideModal
    v-model="data.sampleReportOpen"
    :close-on-outside-click="true"
    width="80%"
  >
    <template #title>
      Results for
      {{
        (data.selectedSample ? app.model.outputs.sampleLabels?.[data.selectedSample] : undefined) ??
          '...'
      }}
    </template>
    <SampleReportPanel v-model="data.selectedSample" />
  </PlSlideModal>
</template>
