import { platforma } from "@platforma-open/cellecta.drivermap-mixcr-clonotyping.model";
import { defineAppV3 } from "@platforma-sdk/ui-vue";
import MainPage from "./pages/MainPage.vue";

export const sdkPlugin = defineAppV3(platforma, (app) => {
  return {
    progress: () => {
      return app.model.outputs.isRunning;
    },
    showErrorsNotification: true,
    routes: {
      "/": () => MainPage,
    },
  };
});

export const useApp = sdkPlugin.useApp;
