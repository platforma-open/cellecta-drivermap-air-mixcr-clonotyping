import type { InferOutputsType, PlRef } from '@platforma-sdk/model';
import { BlockModel, isPColumnSpec, parseResourceMap } from '@platforma-sdk/model';

export type BlockArgs = {
  input?: PlRef;
  preset?: string;
  limitInput?: number;
};

export type UiState = {
  title?: string;
};

export const ProgressPrefix = '[==PROGRESS==]';

export const ProgressPattern
  = /(?<stage>[^:]*):(?: *(?<progress>[0-9.]+)%)?(?: *ETA: *(?<eta>.+))?/;

export const model = BlockModel.create()

  .withArgs<BlockArgs>({})
  .withUiState<UiState>({
    title: 'DriverMap™ AIR Profiling',
  })

  .argsValid((ctx) =>
    ctx.args.input !== undefined && ctx.args.preset !== undefined,
  )

  .retentiveOutput('inputOptions', (ctx) => {
    return ctx.resultPool.getOptions((v) => {
      if (!isPColumnSpec(v)) return false;
      const domain = v.domain;
      return (
        v.name === 'pl7.app/sequencing/data'
        && (v.valueType as string) === 'File'
        && domain !== undefined
        && (domain['pl7.app/fileExtension'] === 'fasta'
          || domain['pl7.app/fileExtension'] === 'fasta.gz'
          || domain['pl7.app/fileExtension'] === 'fastq'
          || domain['pl7.app/fileExtension'] === 'fastq.gz')
      );
    });
  })

  // @TODO: remove from outputs
  .output('clones', (ctx) => {
    return ctx.outputs?.resolve('clones');
  })
  // @TODO: remove from outputs
  .output('clns', (ctx) => {
    return ctx.outputs?.resolve('clns');
  })

  .output('sampleLabels', (ctx): Record<string, string> | undefined => {
    const inputRef = ctx.args.input;
    if (inputRef === undefined) return undefined;

    const spec = ctx.resultPool.getPColumnSpecByRef(inputRef);
    if (spec === undefined) return undefined;

    return ctx.resultPool.findLabelsForColumnAxis(spec, 0);
  })

  .output('logs', (ctx) => {
    return parseResourceMap(ctx.outputs?.resolve('logs'), (acc) => acc.getLogHandle(), false);
  })

  .output('progress', (ctx) => {
    return parseResourceMap(ctx.outputs?.resolve('logs'), (acc) => acc.getProgressLog(ProgressPrefix), false);
  })

  .output('qc', (ctx) =>
    parseResourceMap(ctx.outputs?.resolve('qc'), (acc) => acc.getFileHandle(), true),
  )

  .output('reports', (ctx) =>
    parseResourceMap(ctx.outputs?.resolve('reports'), (acc) => acc.getFileHandle(), false),
  )

  .output('isRunning', (ctx) => ctx.outputs?.getIsReadyOrError() === false)

  .sections((_) => [{ type: 'link', href: '/', label: 'Main' }])

  .title((ctx) => ctx.uiState.title ?? 'DriverMap™ AIR Profiling')

  .done();

export type BlockOutputs = InferOutputsType<typeof model>;
