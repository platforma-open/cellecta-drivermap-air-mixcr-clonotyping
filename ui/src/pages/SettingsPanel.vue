<script setup lang="ts">
import { plRefsEqual, type PlRef } from "@platforma-sdk/model";
import {
  PlAccordionSection,
  PlAlert,
  PlDropdown,
  PlDropdownMulti,
  PlDropdownRef,
  PlNumberField,
  PlSectionSeparator,
} from "@platforma-sdk/ui-vue";
import { useApp } from "../app";
import StepResourcesSettings from "./StepResourcesSettings.vue";

const app = useApp();

function setInput(inputRef?: PlRef) {
  app.model.data.input = inputRef;
  if (inputRef)
    app.model.data.title =
      "DriverMap™ AIR Profiling - " +
      app.model.outputs.inputOptions?.find((o) => plRefsEqual(o.ref, inputRef))?.label;
  else app.model.data.title = undefined;
}

const receptorOrChainsOptions = [
  { value: "IG", label: "IG" },
  { value: "TCRAB", label: "TCR-αβ" },
  { value: "TCRGD", label: "TCR-ɣδ" },

  { value: "IGHeavy", label: "IG Heavy" },
  { value: "IGLight", label: "IG Light" },
  { value: "TCRAlpha", label: "TCR-α" },
  { value: "TCRBeta", label: "TCR-β" },
  { value: "TCRGamma", label: "TCR-ɣ" },
  { value: "TCRDelta", label: "TCR-δ" },
];

const presetOptions = [
  { label: "DriverMap™ AIR RNA Profiling", value: "cellecta-human-rna-xcr-mivbc-drivermap-air-v2" },
  {
    label: "DriverMap™ AIR RNA Full-Length Profiling",
    value: "cellecta-human-rna-xcr-full-length-mivbc-drivermap-air-v2",
  },
  { label: "DriverMap™ AIR DNA Profiling", value: "cellecta-human-dna-xcr-mivbc-drivermap-air-v2" },
];
</script>

<template>
  <PlDropdownRef
    v-model="app.model.data.input"
    :options="app.model.outputs.inputOptions"
    label="Select dataset"
    clearable
    @update:model-value="setInput"
  />

  <PlDropdown v-model="app.model.data.preset" :options="presetOptions" label="Preset" required />
  <PlAlert v-if="app.model.outputs.presetSupport?.supported === false" type="error">
    {{ app.model.outputs.presetSupport.reason }}
  </PlAlert>

  <PlDropdownMulti
    v-model="app.model.data.chains"
    label="Receptors"
    :options="receptorOrChainsOptions"
  >
    <template #tooltip> Restrict the analysis to certain receptor types. </template>
  </PlDropdownMulti>

  <PlAccordionSection label="Advanced Settings">
    <PlNumberField
      v-model="app.model.data.limitInput"
      clearable
      label="Take only this number of reads into analysis"
    />

    <PlSectionSeparator>Resources</PlSectionSeparator>
    <PlNumberField
      v-model="app.model.data.perProcessMemGB"
      label="Set memory per every sample process (GB)"
      :min-value="1"
      :step="1"
      clearable
    >
      <template #tooltip>
        Replaces the computed memory of every MiXCR step that sets no per-step value below.
      </template>
    </PlNumberField>
    <PlNumberField
      v-model="app.model.data.perProcessCPUs"
      label="Set CPU number per every sample process"
      :min-value="1"
      :step="1"
      clearable
    />
    <PlAccordionSection label="Per-step resources">
      <StepResourcesSettings />
    </PlAccordionSection>
  </PlAccordionSection>
</template>
