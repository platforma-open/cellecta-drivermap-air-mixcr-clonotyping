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
  TreeNodeAccessor,
  createPlDataTableStateV2,
  createPlDataTableV3,
  isPColumnSpec,
  parseResourceMap,
  type PColumnKey,
  type PColumnResourceMapData,
} from "@platforma-sdk/model";
import { kind } from "@platforma-open/cellecta.drivermap-mixcr-clonotyping.kind";
import type { BlockArgs, StepResources } from "./args";
import { StepResources as StepResourcesSchema } from "./args";
import { ProgressPrefix } from "./progress";
import type { PresetSupport, StepDefaults } from "./step-resources";
import { dropEmptyOverrides } from "./step-resources";

/** Legacy V1 args shape — consumed only by the legacy upgrader. */
type LegacyArgs = {
  input?: PlRef;
  preset?: string;
  limitInput?: number;
  chains: string[];
};

/** Legacy V1 UI-state shape — consumed only by the legacy upgrader. */
type LegacyUiState = {
  title?: string;
};

/** The first V3 data shape: the V1 args plus the UI title. */
type BlockDataV1 = LegacyArgs & {
  title?: string;
};

export type BlockData = BlockDataV1 & {
  perProcessMemGB?: number;
  perProcessCPUs?: number;
  stepResources?: StepResources;
  /** The preset the "Per-step resources" settings last listed steps for. A snapshot taken on
   * the operator's click, so the step plan runs once per click and never for an operator who
   * did not ask. Absent until then. */
  listStepsPreset?: string;
  tableState: PlDataTableStateV2;
};

const dataModel = new DataModelBuilder({ kind })
  .from<BlockDataV1>("v1")
  .upgradeLegacy<LegacyArgs, LegacyUiState>(({ args, uiState }) => ({
    ...args,
    title: uiState.title,
  }))
  .migrate<BlockData>("v2", (v1) => ({ ...v1, tableState: createPlDataTableStateV2() }))
  // `params` is absent when a block is created by hand rather than from a template, so every
  // field the contract carries keeps its own default.
  .init(({ params }) => ({
    ...params,
    chains: params?.chains ?? ["IG", "TCRAB", "TCRGD"],
    title: params?.title ?? "DriverMap™ AIR Profiling",
    tableState: createPlDataTableStateV2(),
  }));

/**
 * Reads the per-sample `logs` column: a map of streams keyed by MiXCR step. Entries are keyed
 * [sampleId, step]; a sample whose value is a single stream is keyed [sampleId].
 */
function parseSampleLogs<T>(
  acc: TreeNodeAccessor | undefined,
  parse: (acc: TreeNodeAccessor) => T | undefined,
): PColumnResourceMapData<NonNullable<T>> | undefined {
  if (acc === undefined) return undefined;
  const data: { key: PColumnKey; value: NonNullable<T> }[] = [];
  let isComplete = acc.getInputsLocked();
  for (const sampleKey of acc.listInputFields()) {
    const sample = acc.resolve({ field: sampleKey, assertFieldType: "Input" });
    if (sample === undefined) {
      isComplete = false;
      continue;
    }
    const key = JSON.parse(sampleKey) as PColumnKey;
    if (sample.resourceType.name === RT_RESOURCE_MAP) {
      const steps = parseResourceMap(sample, parse, false);
      isComplete &&= steps.isComplete;
      for (const step of steps.data) data.push({ key: [...key, ...step.key], value: step.value });
    } else {
      const value = parse(sample);
      if (value === undefined || value === null) isComplete = false;
      else data.push({ key, value });
    }
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

  .retentiveOutput("inputOptions", (ctx) => {
    return ctx.resultPool.getOptions((v) => {
      if (!isPColumnSpec(v)) return false;
      const domain = v.domain;
      return (
        v.name === "pl7.app/sequencing/data" &&
        (v.valueType as string) === "File" &&
        domain !== undefined &&
        (domain["pl7.app/fileExtension"] === "fasta" ||
          domain["pl7.app/fileExtension"] === "fasta.gz" ||
          domain["pl7.app/fileExtension"] === "fastq" ||
          domain["pl7.app/fileExtension"] === "fastq.gz")
      );
    });
  })

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

  .output("progress", (ctx) =>
    parseSampleLogs(ctx.outputs?.resolve("logs"), (acc) => acc.getProgressLog(ProgressPrefix)),
  )

  .output("qc", (ctx) =>
    parseResourceMap(ctx.outputs?.resolve("qc"), (acc) => acc.getFileHandle(), true),
  )

  .output("reports", (ctx) =>
    parseResourceMap(ctx.outputs?.resolve("reports"), (acc) => acc.getFileHandle(), false),
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

    // Channel 2: a per-sample VBC step error inside the nested `vbcStatus` map.
    // Wrapped defensively — `parseResourceMap` throws on an unexpected resource
    // shape, and an unexpected shape must not crash this status output.
    const vbc = outputs.resolve("vbcStatus");
    if (vbc !== undefined) {
      let vbcFailed = false;
      try {
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
        vbcFailed = byChain.data.length > 0;
      } catch {
        vbcFailed = false;
      }
      if (vbcFailed) {
        throw new Error("VBC clonotype processing failed for one or more samples.");
      }
    }

    return true;
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
    if (cols.length === 0) return undefined;
    // A single primary column avoids V3's per-primary label-discovery collision on same-axis
    // columns.
    return createPlDataTableV3(ctx, {
      primaryColumns: [cols[0]],
      columns: cols.slice(1),
      tableState: ctx.data.tableState,
    });
  })

  .sections((_ctx) => [
    { type: "link", href: "/", label: "Main" },
    { type: "link", href: "/qc-report-table", label: "QC Report Table" },
  ])

  .title((ctx) => ctx.data.title ?? "DriverMap™ AIR Clonotyping")

  .done();

export type BlockOutputs = InferOutputsType<typeof platforma>;
export type Href = InferHrefType<typeof platforma>;
export * from "./args";
export * from "./progress";
export * from "./qc";
export * from "./reports";
export * from "./step-resources";
