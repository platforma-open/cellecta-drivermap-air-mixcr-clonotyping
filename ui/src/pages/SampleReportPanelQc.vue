<script setup lang="ts">
import { computed } from 'vue';
import QcSection from '../components/QcSection.vue';
import type { Result } from '../results';
const props = defineProps<{
  sampleData: Result;
}>();

const qc = computed(() => props.sampleData.qc);
</script>

<template>
  <div>
    <QcSection v-for="(it, i) in qc" :key="i" :value="it" />
  </div>
</template>
