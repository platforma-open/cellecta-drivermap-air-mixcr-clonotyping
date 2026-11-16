<script setup lang="ts">
import { PlAccordion, PlAccordionSection, PlLogView } from "@platforma-sdk/ui-vue";
import { computed, reactive } from "vue";
import type { Result } from "../results";

const props = defineProps<{
  sampleData: Result;
}>();

// The MiXCR steps in run order, then the VBC filter and normalize steps that follow them.
const allLogs = computed(() => [...props.sampleData.logs, ...props.sampleData.vbcLogs]);

// Every step's section opens by default; the user collapses the ones read.
const collapsed = reactive<Record<string, boolean>>({});
</script>

<template>
  <!-- One section per MiXCR step, then per VBC step, in run order. A section honours its model-value only inside a
       PlAccordion with `multiple`; standalone it keeps its own closed state. -->
  <PlAccordion v-if="allLogs.length > 1" multiple>
    <PlAccordionSection
      v-for="log in allLogs"
      :key="log.key"
      :label="log.label"
      :model-value="!collapsed[log.key]"
      @update:model-value="collapsed[log.key] = !$event"
    >
      <PlLogView :log-handle="log.handle" />
    </PlAccordionSection>
  </PlAccordion>
  <PlLogView v-else :log-handle="allLogs[0]?.handle" />
</template>
