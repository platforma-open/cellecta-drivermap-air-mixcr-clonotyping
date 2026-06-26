import type { InferOutputsType, PlRef } from "@platforma-sdk/model";
import {
  BlockModelV3,
  DataModelBuilder,
  isPColumnSpec,
  parseResourceMap,
} from "@platforma-sdk/model";

/** Workflow-relevant args projected out of {@link BlockData} by `.args`. */
export type BlockArgs = {
  input?: PlRef;
  preset?: string;
  limitInput?: number;
  chains: string[];
};

/** Legacy V1 UI-state shape — consumed only by the legacy upgrader. */
export type LegacyUiState = {
  title?: string;
};

/**
 * Unified V3 block data: the workflow args plus the UI-only block title.
 * `title` is UI-only and never reaches the workflow (stripped in `.args`).
 */
export type BlockData = BlockArgs & {
  title?: string;
};

export const ProgressPrefix = "[==PROGRESS==]";

export const ProgressPattern =
  /(?<stage>[^:]*):(?: *(?<progress>[0-9.]+)%)?(?: *ETA: *(?<eta>.+))?/;

const dataModel = new DataModelBuilder()
  .from<BlockData>("v1")
  .upgradeLegacy<BlockArgs, LegacyUiState>(({ args, uiState }) => ({
    ...args,
    title: uiState.title,
  }))
  .init(() => ({
    chains: ["IG", "TCRAB", "TCRGD"],
    title: "DriverMap™ AIR Profiling",
  }));

export const platforma = BlockModelV3.create(dataModel)

  .args<BlockArgs>((data) => {
    if (data.input === undefined) throw new Error("Input dataset is required");
    if (data.preset === undefined) throw new Error("Preset is required");
    return {
      input: data.input,
      preset: data.preset,
      limitInput: data.limitInput,
      chains: data.chains,
    };
  })

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

  .output("logs", (ctx) => {
    return parseResourceMap(ctx.outputs?.resolve("logs"), (acc) => acc.getLogHandle(), false);
  })

  .output("progress", (ctx) => {
    return parseResourceMap(
      ctx.outputs?.resolve("logs"),
      (acc) => acc.getProgressLog(ProgressPrefix),
      false,
    );
  })

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

  .sections((_ctx) => [{ type: "link", href: "/", label: "Main" }])

  .title((ctx) => ctx.data.title ?? "DriverMap™ AIR Clonotyping")

  .done();

export type BlockOutputs = InferOutputsType<typeof platforma>;
