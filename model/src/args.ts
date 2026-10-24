import type { PlRef } from "@platforma-sdk/model";
import { z } from "zod";

/** Per-step replacement of the workflow's sizing rule; an unset field keeps the rule's value. */
export const StepResourceOverride = z
  .object({
    memFloor: z.number().int().gte(1).optional(),
    memIntercept: z.number().int().gte(0).optional(),
    memSlope: z.number().gte(0).optional(),
    cap: z.number().int().gte(1).optional(),
    cpuIntercept: z.number().int().gte(1).optional(),
    cpuSlope: z.number().gte(0).optional(),
  })
  .refine((o) => o.cap === undefined || o.memFloor === undefined || o.cap >= o.memFloor, {
    message: "Cap must be at least the memory floor",
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
