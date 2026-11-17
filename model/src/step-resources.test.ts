import { describe, expect, test } from "vitest";
import { dropEmptyOverrides } from "./step-resources";

describe("dropEmptyOverrides", () => {
  test("drops unset fields and empty steps", () => {
    expect(
      dropEmptyOverrides({ assemble: { memFloor: 32 }, qc: { memFloor: undefined }, align: {} }),
    ).toEqual({
      assemble: { memFloor: 32 },
    });
    expect(dropEmptyOverrides({ align: { memFloor: undefined } })).toBeUndefined();
  });
});
