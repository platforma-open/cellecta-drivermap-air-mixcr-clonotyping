import type { StepResources } from "./args";
import { StepResources as StepResourcesSchema } from "./args";

/** The settings the Run gate checks beyond the dataset and the preset. */
export type GatedSettings = {
  chains: string[];
  limitInput?: number;
  perProcessMemGB?: number;
  perProcessCPUs?: number;
  stepResources?: StepResources;
};

const NUMBER_FIELDS = [
  ["limitInput", "The number of reads to take"],
  ["perProcessMemGB", "The minimum memory per sample process"],
  ["perProcessCPUs", "The CPU number per sample process"],
] as const;

/** Why the block cannot run with these settings, in the words the settings panel shows, or
 * undefined when they are fine. The args projection refuses the same settings. */
export function settingsIssue(data: GatedSettings): string | undefined {
  if (data.chains.length === 0) return "Select at least one receptor.";
  for (const [field, name] of NUMBER_FIELDS) {
    const value = data[field];
    if (value !== undefined && !(Number.isInteger(value) && value > 0))
      return `${name} must be a positive whole number.`;
  }
  if (
    data.stepResources !== undefined &&
    !StepResourcesSchema.safeParse(data.stepResources).success
  )
    return "A per-step memory floor must be a positive whole number.";
  return undefined;
}
