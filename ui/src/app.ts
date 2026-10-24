import { platforma } from "@platforma-open/cellecta.drivermap-mixcr-clonotyping.model";
import { defineAppV3 } from "@platforma-sdk/ui-vue";
import MainPage from "./pages/MainPage.vue";
import QcReportTablePage from "./pages/QcReportTablePage.vue";

export const sdkPlugin = defineAppV3(platforma, (app) => {
  return {
    progress: () => {
      return app.model.outputs.isRunning;
    },
    showErrorsNotification: true,
    routes: {
      "/": () => MainPage,
      "/qc-report-table": () => QcReportTablePage,
    },
  };
});

export const useApp = sdkPlugin.useApp;
