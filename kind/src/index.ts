import { assertParamsObject, defineBlockKind } from "@platforma-sdk/block-kind";
import { isPlRef, type PlRef } from "@platforma-sdk/model";
import { name, version } from "../package.json" with { type: "json" };

/**
 * This block's init-params contract — the shape a block of this kind receives
 * at creation, and exactly what a project template serializes for it.
 *
 * Every field is optional: a block with no input picked and no preset chosen is
 * an ordinary state the UI reaches, so export has to be able to write it and
 * apply has to be able to take it back. Whether a configuration is runnable is
 * settled by the model's `args` lambda, not here.
 */
export type BlockParams = {
  input?: PlRef;
  /** A built-in Cellecta DriverMap™ AIR MiXCR preset name. */
  preset?: string;
  chains?: string[];
  limitInput?: number;
  perProcessMemGB?: number;
  perProcessCPUs?: number;
  title?: string;
};

type Guard<T> = (value: unknown) => value is T;
type Check<T> = { readonly is: Guard<T>; readonly must: string };

const isString: Guard<string> = (v): v is string => typeof v === "string";
const isInteger: Guard<number> = (v): v is number => Number.isInteger(v);
const isStringArray: Guard<string[]> = (v): v is string[] =>
  Array.isArray(v) && v.every((e) => typeof e === "string");

/**
 * The contract, field by field, at runtime. The `satisfies` clause demands an
 * entry for every key `BlockParams` declares, typed against that key's own type.
 */
const CONTRACT = {
  input: { is: isPlRef, must: "a reference to another block's output" },
  preset: { is: isString, must: "a string" },
  chains: { is: isStringArray, must: "an array of strings" },
  limitInput: { is: isInteger, must: "an integer" },
  perProcessMemGB: { is: isInteger, must: "an integer" },
  perProcessCPUs: { is: isInteger, must: "an integer" },
  title: { is: isString, must: "a string" },
} satisfies { [K in keyof BlockParams]-?: Check<NonNullable<BlockParams[K]>> };

/**
 * The same contract at runtime, for params that arrive from a template file.
 * Each field the contract names is read and checked; a key it does not name is
 * dropped by never being read.
 */
function parseInitializationParams(value: unknown): BlockParams {
  assertParamsObject(value);

  const params: BlockParams = {};
  for (const [field, check] of Object.entries(CONTRACT)) {
    const raw = value[field];
    if (raw === undefined) continue;
    if (!check.is(raw)) throw new Error(`'${field}' must be ${check.must}.`);
    Object.assign(params, { [field]: raw });
  }
  return params;
}

// Identity (`name`/`version`) comes from this package's own `package.json`, so
// the on-wire `{name}@{version}` reference can never drift from what npm
// publishes; the bundler inlines the JSON import.
export const kind = defineBlockKind<BlockParams>({
  name,
  version,
  parseInitializationParams,
});
