import type { PlRef } from "@platforma-sdk/model";
import { z } from "zod";

/** Per-step replacement of the workflow's memory floor, in GiB; unset keeps the rule's floor. */
export const StepResourceOverride = z.object({
  memFloor: z.number().int().gte(1).optional(),
});
export type StepResourceOverride = z.infer<typeof StepResourceOverride>;

/** Keyed by step: the MiXCR command. */
export const StepResources = z.record(z.string(), StepResourceOverride);
export type StepResources = z.infer<typeof StepResources>;

/** What the main workflow receives, projected out of `BlockData` by `.args`. */
export type BlockArgs = {
  input: PlRef;
  preset: string;
  limitInput?: number;
  chains: string[];
  perProcessMemGB?: number;
  perProcessCPUs?: number;
  stepResources?: StepResources;
};
