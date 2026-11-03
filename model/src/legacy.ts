import {
  createPlDataTableStateV2,
  type PlDataTableStateV2,
  type PlRef,
} from "@platforma-sdk/model";

/** The V1 args shape, as persisted by block versions before BlockModelV3. */
export type LegacyArgs = {
  input?: PlRef;
  preset?: string;
  limitInput?: number;
  chains?: string[];
};

/** The V1 UI-state shape: the title only. */
export type LegacyUiState = {
  title?: string;
};

export const DEFAULT_CHAINS = ["IG", "TCRAB", "TCRGD"];

/** The V3 data a V1 project starts from. */
export function upgradeLegacyArgs(
  args: LegacyArgs | undefined,
  uiState: LegacyUiState | undefined,
): {
  input?: PlRef;
  preset?: string;
  limitInput?: number;
  chains: string[];
  title?: string;
  tableState: PlDataTableStateV2;
} {
  return {
    input: args?.input,
    preset: args?.preset,
    limitInput: args?.limitInput,
    chains: args?.chains ?? DEFAULT_CHAINS,
    title: uiState?.title,
    tableState: createPlDataTableStateV2(),
  };
}
