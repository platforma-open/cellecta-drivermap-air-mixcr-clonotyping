import { describe, expect, test } from "vitest";
import { sampleProgress, type SampleState } from "./status";

const idle: SampleState = {
  blockRunning: false,
  blockErrored: false,
  mixcrDone: false,
  started: false,
  vbcFailed: false,
};

describe("sampleProgress", () => {
  test.for<[string, Partial<SampleState>, string]>([
    ["not started", {}, "Not started"],
    ["queued", { blockRunning: true }, "Queued"],
    [
      "MiXCR running",
      { blockRunning: true, started: true, mixcrProgress: "Alignment: 40%" },
      "Alignment: 40%",
    ],
    ["MiXCR running, no progress line", { blockRunning: true, started: true }, "Running"],
    ["post-MiXCR", { blockRunning: true, started: true, mixcrDone: true }, "Processing clonotypes"],
    ["done", { started: true, mixcrDone: true }, "Done"],
    ["MiXCR failed on it", { blockErrored: true, started: true }, "Error"],
    [
      "VBC failed on it",
      { blockErrored: true, started: true, mixcrDone: true, vbcFailed: true },
      "Error",
    ],
    ["failed elsewhere", { blockErrored: true, started: true, mixcrDone: true }, "Stopped"],
    ["never started in a failed run", { blockErrored: true }, "Not started"],
  ])("%s", ([, state, expected]) => {
    expect(sampleProgress({ ...idle, ...state })).toBe(expected);
  });
});
