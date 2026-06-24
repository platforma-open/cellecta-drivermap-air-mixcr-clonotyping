<script lang="ts" setup>
import type { AlignReport } from "@platforma-open/milaboratories.mixcr-clonotyping-2.model";
import { PlChartStackedBar } from "@platforma-sdk/ui-vue";
import { toRef } from "vue";
import { useChainsChartSettings } from "./chainsChartSettings";

const props = defineProps<{
  alignReport?: AlignReport;
}>();

const settings = useChainsChartSettings(toRef(props, "alignReport"));
</script>

<template>
  <PlChartStackedBar :settings="settings" />
</template>
