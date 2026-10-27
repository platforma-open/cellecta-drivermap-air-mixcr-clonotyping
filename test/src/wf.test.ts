import type {
  BlockData,
  BlockOutputs,
  platforma,
} from "@platforma-open/cellecta.drivermap-mixcr-clonotyping.model";
import { AlignReport, Qc } from "@platforma-open/cellecta.drivermap-mixcr-clonotyping.model";
import { SamplesAndDataBlockPointer } from "@platforma-open/milaboratories.samples-and-data";
import type { InferBlockState } from "@platforma-sdk/model";
import { createPlDataTableStateV2, uniquePlId, wrapOutputs } from "@platforma-sdk/model";
import { awaitStableState, blockTest } from "@platforma-sdk/test";
import { DrivermapMixcrClonotypingBlockPointer as myBlockSpec } from "this-block";

blockTest("empty inputs", { timeout: 30000 }, async ({ rawPrj: project, expect }) => {
  const blockId = await project.addBlock("Block", myBlockSpec);
  const state = (await awaitStableState(project.getBlockState(blockId), 25000)) as InferBlockState<
    typeof platforma
  >;
  expect(state.outputs).toMatchObject({ inputOptions: { ok: true, value: [] } });
  const outputs = wrapOutputs<BlockOutputs>(state.outputs);
  expect(outputs.logs).toBeUndefined();
});

// One sample of Cellecta-shaped reads (test/assets/make_synthetic_cellecta.py) through the RNA
// profiling preset: MiXCR split into one exec per step, then export, the VBC filter and
// normalization, aggregation, and the QC report table.
blockTest(
  "rna profiling",
  { timeout: 600000 },
  async ({ rawPrj: project, ml, helpers, expect }) => {
    const sndBlockId = await project.addBlock("Samples & Data", SamplesAndDataBlockPointer);
    const sampleId = uniquePlId();
    const r1Handle = await helpers.getLocalFileHandle("./assets/synthetic_cellecta_R1.fastq.gz");
    const r2Handle = await helpers.getLocalFileHandle("./assets/synthetic_cellecta_R2.fastq.gz");
    await project.mutateBlockStorage(sndBlockId, {
      operation: "update-block-data",
      value: {
        metadata: [],
        sampleIds: [sampleId],
        sampleLabelColumnLabel: "Sample Name",
        sampleLabels: { [sampleId]: "Sample 1" },
        datasets: [
          {
            id: uniquePlId(),
            label: "Dataset 1",
            content: {
              type: "Fastq",
              readIndices: ["R1", "R2"],
              gzipped: true,
              data: { [sampleId]: { R1: r1Handle, R2: r2Handle } },
            },
          },
        ],
        h5adFilesToPreprocess: [],
        seuratFilesToPreprocess: [],
        suggestedImport: false,
        // The facade bundles PlId's brand under its own zod symbol, so no satisfies here.
      },
    });

    const blockId = await project.addBlock("DriverMap", myBlockSpec);
    await project.runBlock(sndBlockId);
    await helpers.awaitBlockDone(sndBlockId, 30000);

    const state1 = (await awaitStableState(
      project.getBlockState(blockId),
      25000,
    )) as InferBlockState<typeof platforma>;
    const outputs1 = wrapOutputs<BlockOutputs>(state1.outputs);
    expect(outputs1.inputOptions).toHaveLength(1);

    await project.mutateBlockStorage(blockId, {
      operation: "update-block-data",
      value: {
        input: outputs1.inputOptions![0].ref,
        preset: "cellecta-human-rna-xcr-mivbc-drivermap-air-v2",
        chains: ["IGHeavy"],
        title: "DriverMap",
        // A lowered floor shows a per-step override reaching the step.
        stepResources: { assemble: { memFloor: 4 } },
        tableState: createPlDataTableStateV2(),
      } satisfies BlockData,
    });

    await project.runBlock(blockId);
    const state2 = await helpers.awaitBlockDoneAndGetStableBlockState(blockId, 500000);
    const outputs2 = wrapOutputs<BlockOutputs>(state2.outputs as unknown as BlockOutputs);

    expect(outputs2.clonotypingStatus).toBe(true);

    // One log per MiXCR step, keyed [sampleId, step], in run order.
    const steps = outputs2
      .logs!.data.filter((e) => e.key[0] === sampleId)
      .map((e) => String(e.key[1]))
      .sort();
    expect(steps).toEqual(["001:align", "002:refineTagsAndSort", "003:assemble", "004:qc"]);

    const alignEntry = outputs2.reports.data.find(
      (e) => e.key[1] === "align" && e.key[2] === "json",
    );
    const alignReport = AlignReport.parse(
      JSON.parse(
        Buffer.from(
          await ml.driverKit.blobDriver.getContent(
            alignEntry!.value!.handle as Parameters<typeof ml.driverKit.blobDriver.getContent>[0],
          ),
        ).toString("utf8"),
      ),
    );
    expect(alignReport.aligned).greaterThan(100);

    const qcEntry = outputs2.qc!.data.find((e) => e.key[0] === sampleId);
    const qc = Qc.parse(
      JSON.parse(
        Buffer.from(
          await ml.driverKit.blobDriver.getContent(
            qcEntry!.value!.handle as Parameters<typeof ml.driverKit.blobDriver.getContent>[0],
          ),
        ).toString("utf8"),
      ),
    );
    expect(qc.length).greaterThan(0);

    // The QC report table: one row for the one sample.
    const tableHandle = outputs2.qcReportTable?.fullTableHandle;
    expect(tableHandle).toBeDefined();
    const shape = await ml.driverKit.pFrameDriver.getShape(tableHandle!);
    expect(shape.rows).toEqual(1);
  },
);
