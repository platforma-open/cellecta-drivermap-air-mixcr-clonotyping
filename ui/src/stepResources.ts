import type { StepRule } from "@platforma-open/cellecta.drivermap-mixcr-clonotyping.model";
import { computed } from "vue";
import { resultMap } from "./results";

// Step logs arrive keyed by (sampleId, logKey); the workflow leads each logKey with the step's
// zero-padded run position (`003:assemble`), so sorting by it gives the run order.

function stepOf(logKey: string): string {
  return logKey.slice(logKey.indexOf(":") + 1);
}

/** A step the settings can edit, with its default rule when one is known. */
export type KnownStep = { step: string; defaultRule?: StepRule };

/** The step names of every finished run's logs, in run order: what the settings editor lists
 * when the prerun has not planned the preset. Their default rules are unknown then. */
export const KnownSteps = computed(() => {
  const seen = new Map<string, KnownStep>();
  for (const result of resultMap.value?.values() ?? [])
    for (const log of result.logs) {
      const step = stepOf(log.key);
      if (!seen.has(step)) seen.set(step, { step });
    }
  return [...seen.values()];
});
