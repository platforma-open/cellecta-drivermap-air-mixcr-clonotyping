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

  // @TODO: remove from outputs
  .output("clones", (ctx) => {
    return ctx.outputs?.resolve("clones");
  })
  // @TODO: remove from outputs
  .output("clns", (ctx) => {
    return ctx.outputs?.resolve("clns");
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

  // Block-level error signal: true once any workflow output has settled into an
  // error — a failed clone export or VBC Python step after MiXCR succeeded
  // (surfaces on the `clones` p-frame, built from the VBC outputs), or MiXCR
  // itself failing (surfaces on the mixcr outputs). `isRunning` alone cannot tell
  // success from failure, because `getIsReadyOrError()` flips to `true` on both;
  // the results table needs this to avoid a green "Done" on a failed run. The keys
  // are the resolvable `ctx.outputs` fields from `main.tpl.tengo` (`clones` =
  // `exportFrame` of the clonotypes frame).
  .output("isErrored", (ctx): boolean => {
    const outputs = ctx.outputs;
    if (outputs === undefined) return false;
    for (const key of ["clones", "clns", "qc", "logs", "reports"]) {
      if (outputs.resolve(key)?.getError() !== undefined) return true;
    }
    return false;
  })

  .sections((_ctx) => [{ type: "link", href: "/", label: "Main" }])

  .title((ctx) => ctx.data.title ?? "DriverMap™ AIR Clonotyping")

  .done();

export type BlockOutputs = InferOutputsType<typeof platforma>;
