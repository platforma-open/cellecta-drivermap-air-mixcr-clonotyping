<script setup lang="ts">
import type { AlignReport } from "@platforma-open/milaboratories.mixcr-clonotyping-2.model";
import { PlChartStackedBar } from "@platforma-sdk/ui-vue";
import { toRef } from "vue";
import { useAlignmentChartSettings } from "./alignmentChartSettings";

const props = defineProps<{
  alignReport?: AlignReport;
}>();

const settings = useAlignmentChartSettings(toRef(props, "alignReport"));
</script>

<template>
  <PlChartStackedBar :settings="settings" />
</template>
