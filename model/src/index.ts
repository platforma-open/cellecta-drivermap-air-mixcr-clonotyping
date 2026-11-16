import type {
  InferHrefType,
  InferOutputsType,
  PlDataTableStateV2,
  PlRef,
} from "@platforma-sdk/model";
import {
  BlockModelV3,
  ColumnsCollection,
  DataModelBuilder,
  RT_RESOURCE_MAP,
  RT_RESOURCE_MAP_PARTITIONED,
  TreeNodeAccessor,
  createPlDataTableStateV2,
  createPlDataTableV3,
  isPColumnSpec,
  parseResourceMap,
  type PColumnKey,
  type PColumnResourceMapData,
  type PObjectSpec,
} from "@platforma-sdk/model";
import { kind } from "@platforma-open/cellecta.drivermap-mixcr-clonotyping.kind";
import type { BlockArgs, StepResources } from "./args";
import { StepResources as StepResourcesSchema } from "./args";
import { DEFAULT_CHAINS, upgradeLegacyArgs, type LegacyArgs, type LegacyUiState } from "./legacy";
import { ProgressPrefix } from "./progress";
import type { PresetSupport, StepDefaults } from "./step-resources";
import { dropEmptyOverrides } from "./step-resources";

export type BlockData = {
  input?: PlRef;
  preset?: string;
  limitInput?: number;
  chains: string[];
  /** Set by the UI from the input's label when the input is picked. */
  title?: string;
  perProcessMemGB?: number;
  perProcessCPUs?: number;
  stepResources?: StepResources;
  /** The preset the "Per-step resources" settings last listed steps for. A snapshot taken on
   * the operator's click, so the step plan runs once per click and never for an operator who
   * did not ask. Absent until then. */
  listStepsPreset?: string;
  tableState: PlDataTableStateV2;
};

const QC_PRIMARY_COLUMN = "mixcr.com/reports/MiXCRVersion";
export const DEFAULT_TITLE = "DriverMap™ AIR Profiling";

const dataModel = new DataModelBuilder({ kind })
  .from<BlockData>("v1")
  .upgradeLegacy<LegacyArgs, LegacyUiState>(({ args, uiState }) => upgradeLegacyArgs(args, uiState))
  // `params` is absent when a block is created by hand rather than from a template, so every
  // field the contract carries keeps its own default.
  .init(({ params }) => ({
    ...params,
    chains: params?.chains ?? DEFAULT_CHAINS,
    tableState: createPlDataTableStateV2(),
  }));

/** The reads columns the block takes as input. */
function isReadsColumn(v: PObjectSpec): boolean {
  if (!isPColumnSpec(v)) return false;
  const ext = v.domain?.["pl7.app/fileExtension"];
  return (
    v.name === "pl7.app/sequencing/data" &&
    (v.valueType as string) === "File" &&
    (ext === "fasta" || ext === "fasta.gz" || ext === "fastq" || ext === "fastq.gz")
  );
}

/** Resolves an input field, or reports "error" when the field or the resource it holds failed:
 * resolving a field that carries an error and no value throws even with `ignoreError`. */
function resolveOrError(
  acc: TreeNodeAccessor,
  field: string,
): TreeNodeAccessor | undefined | "error" {
  try {
    const value = acc.resolve({ field, assertFieldType: "Input", ignoreError: true });
    return value?.getError() !== undefined ? "error" : value;
  } catch {
    return "error";
  }
}

/** Resolves a workflow output that a run made before the MiXCR step split does not have. Such a
 * run's outputs are locked without the field, which reads as undefined here, not as an error. */
function resolveSinceSplit(
  outputs: TreeNodeAccessor | undefined,
  field: string,
): TreeNodeAccessor | undefined {
  return outputs?.resolve({ field, assertFieldType: "Input", allowPermanentAbsence: true });
}

/** The per-sample tables of a [chain] -> [sampleId] -> file map, or undefined until every
 * entry has settled. A sample whose step failed has no table and is left out. */
function sampleTables(byChain: TreeNodeAccessor | undefined, stage: "mixcr" | "vbc") {
  if (byChain === undefined || !byChain.getInputsLocked()) return undefined;
  const tables = [];
  for (const chainKey of byChain.listInputFields()) {
    const chain = resolveOrError(byChain, chainKey);
    if (chain === "error") continue;
    if (chain === undefined || !chain.getInputsLocked()) return undefined;
    for (const sampleKey of chain.listInputFields()) {
      const file = resolveOrError(chain, sampleKey);
      if (file === "error") continue;
      if (file === undefined) return undefined;
      tables.push({
        sampleId: String((JSON.parse(sampleKey) as PColumnKey)[0]),
        chain: String((JSON.parse(chainKey) as PColumnKey)[0]),
        stage,
        handle: file.getRemoteFileHandle(),
      });
    }
  }
  return tables;
}

/** Walks a resource map into `data`. An entry whose field or resource failed is left out, so
 * one failed sample does not take the other samples' entries with it. Returns whether every
 * remaining entry has its value. */
function collectSettled<T>(
  acc: TreeNodeAccessor,
  parse: (acc: TreeNodeAccessor) => T | undefined,
  data: { key: PColumnKey; value: NonNullable<T> }[],
  keyPrefix: PColumnKey,
): boolean {
  const type = acc.resourceType.name;
  if (type !== RT_RESOURCE_MAP && type !== RT_RESOURCE_MAP_PARTITIONED)
    throw new Error(`Unknown resource type: ${type}`);
  let isComplete = acc.getInputsLocked();
  for (const keyStr of acc.listInputFields()) {
    const value = resolveOrError(acc, keyStr);
    if (value === "error") continue;
    if (value === undefined) {
      isComplete = false;
      continue;
    }
    const key = [...keyPrefix, ...(JSON.parse(keyStr) as PColumnKey)];
    if (type === RT_RESOURCE_MAP_PARTITIONED) {
      isComplete = collectSettled(value, parse, data, key) && isComplete;
      continue;
    }
    const parsed = parse(value);
    if (parsed === undefined || parsed === null) isComplete = false;
    else data.push({ key, value: parsed });
  }
  return isComplete;
}

/** `parseResourceMap` that leaves out the entries of a failed sample instead of throwing. */
function parseSettledMap<T>(
  acc: TreeNodeAccessor | undefined,
  parse: (acc: TreeNodeAccessor) => T | undefined,
): PColumnResourceMapData<NonNullable<T>> {
  const data: { key: PColumnKey; value: NonNullable<T> }[] = [];
  const isComplete = acc !== undefined && collectSettled(acc, parse, data, []);
  return { isComplete, data };
}

/** Reads the per-sample `logs` column: a map of streams keyed by MiXCR step, keyed [sampleId, step].
 * A failed sample is left out. So is the single stream per sample of a run made before MiXCR
 * ran as one job per step: it has no step to list under. */
function parseSampleLogs<T>(
  acc: TreeNodeAccessor | undefined,
  parse: (acc: TreeNodeAccessor) => T | undefined,
): PColumnResourceMapData<NonNullable<T>> | undefined {
  if (acc === undefined) return undefined;
  const data: { key: PColumnKey; value: NonNullable<T> }[] = [];
  let isComplete = acc.getInputsLocked();
  for (const sampleKey of acc.listInputFields()) {
    const sample = resolveOrError(acc, sampleKey);
    if (sample === "error") continue;
    if (sample === undefined) {
      isComplete = false;
      continue;
    }
    const key = JSON.parse(sampleKey) as PColumnKey;
    const type = sample.resourceType.name;
    if (type !== RT_RESOURCE_MAP && type !== RT_RESOURCE_MAP_PARTITIONED) continue;
    isComplete = collectSettled(sample, parse, data, key) && isComplete;
  }
  return { isComplete, data };
}

/** Reads the `vbcLogs` output, [chain] -> [sampleId] -> the VBC filter and normalize streams
 * keyed by step, as entries keyed [sampleId, chain, step]. A chain whose map failed is skipped. */
function parseVbcLogs<T>(
  acc: TreeNodeAccessor | undefined,
  parse: (acc: TreeNodeAccessor) => T | undefined,
): PColumnResourceMapData<NonNullable<T>> | undefined {
  if (acc === undefined) return undefined;
  const data: { key: PColumnKey; value: NonNullable<T> }[] = [];
  let isComplete = acc.getInputsLocked();
  for (const chainKey of acc.listInputFields()) {
    const chainAcc = resolveOrError(acc, chainKey);
    if (chainAcc === "error") continue;
    if (chainAcc === undefined) {
      isComplete = false;
      continue;
    }
    const logs = parseSampleLogs(chainAcc, parse);
    if (logs === undefined) {
      isComplete = false;
      continue;
    }
    isComplete &&= logs.isComplete;
    const [chain] = JSON.parse(chainKey) as PColumnKey;
    for (const { key, value } of logs.data)
      data.push({ key: [key[0], chain, ...key.slice(1)], value });
  }
  return { isComplete, data };
}

export const platforma = BlockModelV3.create({ dataModel, kind })

  // Inverse of `init` — the same fields, projected back out for template export. `tableState`
  // is view state, and a per-step override is tuned to one cluster, so neither crosses.
  .templateParams((data) => ({
    input: data.input,
    preset: data.preset,
    chains: data.chains,
    limitInput: data.limitInput,
    perProcessMemGB: data.perProcessMemGB,
    perProcessCPUs: data.perProcessCPUs,
    title: data.title,
  }))

  .prerunArgs((data) => ({
    preset: data.preset,
    // The step list is planned only for the preset the operator asked it for.
    listSteps: data.listStepsPreset !== undefined && data.listStepsPreset === data.preset,
  }))

  .args<BlockArgs>((data) => {
    if (data.input === undefined) throw new Error("Input dataset is required");
    if (data.preset === undefined) throw new Error("Preset is required");
    if (data.chains.length === 0) throw new Error("Chains selection is required");
    for (const [field, value] of Object.entries({
      limitInput: data.limitInput,
      perProcessMemGB: data.perProcessMemGB,
      perProcessCPUs: data.perProcessCPUs,
    }))
      if (value !== undefined && !(Number.isInteger(value) && value > 0))
        throw new Error(`${field} must be a positive whole number`);
    if (
      data.stepResources !== undefined &&
      !StepResourcesSchema.safeParse(data.stepResources).success
    )
      throw new Error("Per-step resources are invalid");
    return {
      input: data.input,
      preset: data.preset,
      limitInput: data.limitInput,
      chains: data.chains,
      perProcessMemGB: data.perProcessMemGB,
      perProcessCPUs: data.perProcessCPUs,
      stepResources: dropEmptyOverrides(data.stepResources),
    };
  })

  // Whether the block runs the selected preset, known before any run.
  .retentiveOutput("presetSupport", (ctx) =>
    ctx.prerun
      ?.resolve({ field: "presetSupport", assertFieldType: "Input", allowPermanentAbsence: true })
      ?.getDataAsJson<PresetSupport>(),
  )

  // The steps of the selected preset with their default rules, planned before any run.
  .output("stepDefaults", (ctx) =>
    ctx.prerun
      ?.resolve({ field: "stepDefaults", assertFieldType: "Input", allowPermanentAbsence: true })
      ?.getDataAsJson<StepDefaults>(),
  )

  .retentiveOutput("inputOptions", (ctx) => ctx.resultPool.getOptions(isReadsColumn))

  .output("sampleLabels", (ctx): Record<string, string> | undefined => {
    const inputRef = ctx.data.input;
    if (inputRef === undefined) return undefined;

    const spec = ctx.resultPool.getPColumnSpecByRef(inputRef);
    if (spec === undefined) return undefined;

    return ctx.resultPool.findLabelsForColumnAxis(spec, 0);
  })

  // Keyed [sampleId, step].
  .output("logs", (ctx) =>
    parseSampleLogs(ctx.outputs?.resolve("logs"), (acc) => acc.getLogHandle()),
  )

  // Keyed [sampleId, chain, step]: the VBC filter and normalize streams, shown after MiXCR's.
  // A run from a build before this output has no `vbcLogs` field; that reads as no logs.
  .output("vbcLogs", (ctx) =>
    parseVbcLogs(
      ctx.outputs?.resolve({
        field: "vbcLogs",
        assertFieldType: "Input",
        allowPermanentAbsence: true,
      }),
      (acc) => acc.getLogHandle(),
    ),
  )

  .output("progress", (ctx) =>
    parseSampleLogs(ctx.outputs?.resolve("logs"), (acc) => acc.getProgressLog(ProgressPrefix)),
  )

  .output("qc", (ctx) => parseSettledMap(ctx.outputs?.resolve("qc"), (acc) => acc.getFileHandle()))

  .output("reports", (ctx) =>
    parseSettledMap(ctx.outputs?.resolve("reports"), (acc) => acc.getFileHandle()),
  )

  .output("isRunning", (ctx) => ctx.outputs?.getIsReadyOrError() === false)

  // Block-level success/failure signal, exposed as an `OutputWithStatus` envelope
  // so the UI can tell apart "running" (ok, value undefined) / "succeeded"
  // (ok: true) / "failed" (ok: false) — the idiomatic V3 shape, replacing the old
  // bespoke `isErrored` boolean. The lambda throws on a settled failure; the
  // runtime turns the throw into `{ ok: false }`.
  //
  // Two failure channels are covered:
  //   1. Any top-level workflow output field in an error state — MiXCR analyze /
  //      export failing, or a broken `clones` frame root. Scanning every field
  //      (not a hardcoded list) stays correct as outputs are added/renamed.
  //   2. A failed VBC Python step. Those per-sample errors are buried inside the
  //      `clones` exportFrame, where `getError()` on the binary-partitioned
  //      columns cannot reach them, so the workflow surfaces them via `vbcStatus`
  //      — a nested ResourceMap ([chain] -> per-sample cloneTableTsv). We walk
  //      both levels; any entry in an error state means the run failed.
  .outputWithStatus("clonotypingStatus", (ctx) => {
    const outputs = ctx.outputs;
    if (outputs === undefined) return undefined; // not started
    // Judge only once the whole run has settled (success or error). While
    // running, `getIsReadyOrError()` is false and we report ok/undefined.
    if (!outputs.getIsReadyOrError()) return undefined;

    // Channel 1: any output field root errored.
    if (outputs.listOutputFields().some((key) => outputs.resolve(key)?.getError() !== undefined)) {
      throw new Error("Clonotype processing failed. See per-sample logs for details.");
    }

    // Channel 2: a per-sample VBC step error inside the nested `vbcStatus` map. Resolving a
    // field that holds an error throws, and a throw here is the failure this output reports.
    const vbc = resolveSinceSplit(outputs, "vbcStatus");
    if (vbc !== undefined) {
      const byChain = parseResourceMap(
        vbc,
        (chainAcc) => {
          const bySample = parseResourceMap(
            chainAcc,
            (entry) => (entry.getError() !== undefined ? true : undefined),
            false,
          );
          return bySample.data.length > 0 ? true : undefined;
        },
        false,
      );
      if (byChain.data.length > 0) {
        throw new Error("VBC clonotype processing failed for one or more samples.");
      }
    }

    return true;
  })

  // The samples whose VBC step failed, so the UI marks those and not every sample as failed.
  // `vbcStatus` is [chain] -> [sampleId] -> the step's table.
  .output("vbcFailedSamples", (ctx): string[] | undefined => {
    const vbc = resolveSinceSplit(ctx.outputs, "vbcStatus");
    if (vbc === undefined) return undefined;
    const failed = new Set<string>();
    for (const chainKey of vbc.listInputFields()) {
      const chain = resolveOrError(vbc, chainKey);
      if (chain === "error" || chain === undefined) continue;
      for (const sampleKey of chain.listInputFields())
        if (resolveOrError(chain, sampleKey) === "error")
          failed.add(String((JSON.parse(sampleKey) as PColumnKey)[0]));
    }
    return [...failed];
  })

  // Every sample's raw `mixcr exportClones` table and its VBC-filtered table, per chain, for
  // "Export raw results". Undefined until the run has settled.
  .output("rawTables", (ctx) => {
    const mixcr = sampleTables(resolveSinceSplit(ctx.outputs, "mixcrTables"), "mixcr");
    const vbc = sampleTables(resolveSinceSplit(ctx.outputs, "vbcTables"), "vbc");
    return mixcr === undefined || vbc === undefined ? undefined : [...mixcr, ...vbc];
  })

  .outputWithStatus("qcReportTable", (ctx) => {
    const qcReportTable = ctx.outputs?.resolve({
      field: "qcReportTable",
      assertFieldType: "Input",
      allowPermanentAbsence: true,
    });
    if (qcReportTable === undefined) return undefined;
    const collection = ColumnsCollection([qcReportTable]);
    if (collection.isEmpty()) return undefined;
    const cols = collection.getColumns();
    // A single primary column avoids V3's per-primary label-discovery collision on same-axis
    // columns. The others join onto it, so it is one every sample has: each .clns header carries
    // the MiXCR version.
    const primary = cols.find((c) => c.getSpec().name === QC_PRIMARY_COLUMN);
    if (primary === undefined) return undefined;
    return createPlDataTableV3(ctx, {
      primaryColumns: [primary],
      columns: cols.filter((c) => c !== primary),
      tableState: ctx.data.tableState,
    });
  })

  .sections((_ctx) => [
    { type: "link", href: "/", label: "Main" },
    { type: "link", href: "/qc-report-table", label: "QC Report Table" },
  ])

  // The title context carries the data only, not the result pool, so the UI stores the title
  // when the input is picked.
  .title((ctx) => ctx.data.title ?? DEFAULT_TITLE)

  .done();

export type BlockOutputs = InferOutputsType<typeof platforma>;
export type Href = InferHrefType<typeof platforma>;
export * from "./args";
export * from "./progress";
export * from "./qc";
export * from "./reports";
export * from "./status";
export * from "./step-resources";
