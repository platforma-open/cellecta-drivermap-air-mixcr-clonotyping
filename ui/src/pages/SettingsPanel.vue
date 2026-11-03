<script setup lang="ts">
import { DEFAULT_TITLE } from "@platforma-open/cellecta.drivermap-mixcr-clonotyping.model";
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

// The model's title context has no result pool, so the title is stored on the user's pick.
function setInput(inputRef?: PlRef) {
  app.model.data.input = inputRef;
  const label = inputRef
    ? app.model.outputs.inputOptions?.find((o) => plRefsEqual(o.ref, inputRef))?.label
    : undefined;
  app.model.data.title = label === undefined ? undefined : `${DEFAULT_TITLE} - ${label}`;
}

const wholeNumber = (v: number) =>
  Number.isInteger(v) ? undefined : "Value must be a whole number";

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
    :model-value="app.model.data.input"
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
      :min-value="1"
      :step="1"
      :validate="wholeNumber"
      clearable
      label="Take only this number of reads into analysis"
    />

    <PlSectionSeparator>Resources</PlSectionSeparator>
    <PlNumberField
      v-model="app.model.data.perProcessMemGB"
      label="Minimum memory per sample process (GiB)"
      :min-value="1"
      :step="1"
      :validate="wholeNumber"
      clearable
    >
      <template #tooltip>
        Raises the memory floor of every MiXCR step and clone export; a larger input still gets
        more. A per-step floor below wins for its step.
      </template>
    </PlNumberField>
    <PlNumberField
      v-model="app.model.data.perProcessCPUs"
      label="Set CPU number per every sample process"
      :min-value="1"
      :step="1"
      :validate="wholeNumber"
      clearable
    />
    <PlAccordionSection label="Per-step resources">
      <StepResourcesSettings />
    </PlAccordionSection>
  </PlAccordionSection>
</template>
