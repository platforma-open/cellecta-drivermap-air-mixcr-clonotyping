<script lang="ts" setup>
import type { AlignReport } from '@platforma-open/milaboratories.mixcr-clonotyping-2.model';
import { PlChartStackedBar } from '@platforma-sdk/ui-vue';
import { computed } from 'vue';
import { useChainsChartSettings } from './chainsChartSettings';

const props = defineProps<{
  alignReport?: AlignReport;
}>();

const alignReport = computed(() => props.alignReport);

const settings = useChainsChartSettings(alignReport);
</script>

<template>
  <PlChartStackedBar :settings="settings" />
</template>
