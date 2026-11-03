import { describe, expect, test } from "vitest";
import { DEFAULT_CHAINS, upgradeLegacyArgs } from "./legacy";

describe("upgradeLegacyArgs", () => {
  test("carries the V1 args and starts a fresh table state", () => {
    const input = { __isRef: true as const, blockId: "b1", name: "reads" };
    const data = upgradeLegacyArgs(
      {
        input,
        preset: "cellecta-human-rna-xcr-mivbc-drivermap-air-v2",
        limitInput: 1000,
        chains: ["IGHeavy"],
      },
      { title: "DriverMap™ AIR Profiling - Dataset 1" },
    );
    expect(data.input).toEqual(input);
    expect(data.preset).toBe("cellecta-human-rna-xcr-mivbc-drivermap-air-v2");
    expect(data.limitInput).toBe(1000);
    expect(data.chains).toEqual(["IGHeavy"]);
    expect(data.title).toBe("DriverMap™ AIR Profiling - Dataset 1");
    expect(data.tableState).toBeDefined();
  });

  test("defaults the chains when V1 stored none", () => {
    expect(upgradeLegacyArgs({}, {}).chains).toEqual(DEFAULT_CHAINS);
    expect(upgradeLegacyArgs(undefined, undefined).chains).toEqual(DEFAULT_CHAINS);
  });
});
