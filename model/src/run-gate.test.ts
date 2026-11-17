import { expect, test } from "vitest";
import { settingsIssue } from "./run-gate";

test("settings that can run report no issue", () => {
  expect(settingsIssue({ chains: ["IG"] })).toBeUndefined();
  expect(
    settingsIssue({ chains: ["IG"], limitInput: 1000, stepResources: { align: { memFloor: 8 } } }),
  ).toBeUndefined();
});

test("no receptor is an issue", () => {
  expect(settingsIssue({ chains: [] })).toBe("Select at least one receptor.");
});

test("a fractional or non-positive number names its field", () => {
  expect(settingsIssue({ chains: ["IG"], limitInput: 1.5 })).toMatch(/number of reads/);
  expect(settingsIssue({ chains: ["IG"], perProcessMemGB: 0 })).toMatch(/minimum memory/);
  expect(settingsIssue({ chains: ["IG"], perProcessCPUs: -1 })).toMatch(/CPU number/);
});

test("an invalid per-step floor is an issue", () => {
  expect(settingsIssue({ chains: ["IG"], stepResources: { align: { memFloor: 0.5 } } })).toMatch(
    /per-step memory floor/,
  );
});
