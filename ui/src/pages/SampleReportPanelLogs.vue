<script setup lang="ts">
import { PlLogView } from '@platforma-sdk/ui-vue';
import type { Result } from '../results';

const props = defineProps<{
  sampleData: Result;
}>();
</script>

<template>
  <PlLogView :log-handle="props.sampleData.logHandle" />
</template>

<style lang="css">
/** Remove this fix when using ui-vue > v1.8.25 */
.pl-log-view {
    max-height: calc(100% - var(--contour-offset));
    max-width: calc(100% - var(--contour-offset));
}
</style>
