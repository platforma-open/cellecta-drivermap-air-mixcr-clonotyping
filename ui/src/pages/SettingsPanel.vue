<script setup lang="ts">
import { plRefsEqual, type PlRef } from '@platforma-sdk/model';
import { PlAccordionSection, PlDropdown, PlDropdownMulti, PlDropdownRef, PlTextField } from '@platforma-sdk/ui-vue';
import { useApp } from '../app';

const app = useApp();

function setInput(inputRef?: PlRef) {
  app.model.args.input = inputRef;
  if (inputRef)
    app.model.ui.title = 'DriverMap™ AIR Profiling - ' + app.model.outputs.inputOptions?.find((o) => plRefsEqual(o.ref, inputRef))?.label;
  else
    app.model.ui.title = undefined;
}

function parseNumber(v: string): number {
  const parsed = Number(v);

  if (!Number.isFinite(parsed)) {
    throw Error('Not a number');
  }

  return parsed;
}

const receptorOrChainsOptions = [
  { value: 'IG', label: 'IG' },
  { value: 'TCRAB', label: 'TCR-αβ' },
  { value: 'TCRGD', label: 'TCR-ɣδ' },

  { value: 'IGHeavy', label: 'IG Heavy' },
  { value: 'IGLight', label: 'IG Light' },
  { value: 'TCRAlpha', label: 'TCR-α' },
  { value: 'TCRBeta', label: 'TCR-β' },
  { value: 'TCRGamma', label: 'TCR-ɣ' },
  { value: 'TCRDelta', label: 'TCR-δ' },
];

const presetOptions = [
  { label: 'DriverMap™ AIR RNA Profiling', value: 'cellecta-human-rna-xcr-mivbc-drivermap-air-v2' },
  { label: 'DriverMap™ AIR RNA Full-Length Profiling', value: 'cellecta-human-rna-xcr-full-length-mivbc-drivermap-air-v2' },
  { label: 'DriverMap™ AIR DNA Profiling', value: 'cellecta-human-dna-xcr-mivbc-drivermap-air-v2' },
];
</script>

<template>
  <PlDropdownRef
    v-model="app.model.args.input"
    :options="app.model.outputs.inputOptions"
    label="Select dataset"
    clearable @update:model-value="setInput"
  />

  <PlDropdown
    v-model="app.model.args.preset"
    :options="presetOptions"
    label="Preset"
    required
  />

  <PlDropdownMulti v-model="app.model.args.chains" label="Receptors" :options="receptorOrChainsOptions" >
    <template #tooltip>
      Restrict the analysis to certain receptor types.
    </template>
  </PlDropdownMulti>

  <PlAccordionSection label="Advanced Settings">
    <PlTextField
      v-model="app.model.args.limitInput" :parse="parseNumber" :clearable="() => undefined"
      label="Take only this number of reads into analysis"
    />
  </PlAccordionSection>
</template>
