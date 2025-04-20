<script setup lang="ts">
import AlignmentsChart from '../charts/AlignmentsChart.vue';
import ChainsChart from '../charts/ChainsChart.vue';
import type { Result } from '../results';

defineProps<{
  sampleData: Result;
}>();
</script>

<template>
  <AlignmentsChart :align-report="sampleData.alignReport" title="Alignments" />
  <ChainsChart :align-report="sampleData.alignReport" title="Chains distribution" />
</template>
