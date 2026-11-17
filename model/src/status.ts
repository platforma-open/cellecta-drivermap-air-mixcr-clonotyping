/** What the results table knows about one sample when it picks the sample's progress text. */
export type SampleState = {
  /** The whole block is still running. */
  blockRunning: boolean;
  /** The block has settled into a failure. */
  blockErrored: boolean;
  /** MiXCR wrote the sample's qc result: its MiXCR run finished. */
  mixcrDone: boolean;
  /** MiXCR has started on the sample: at least one step log exists. */
  started: boolean;
  /** The sample's VBC step failed. */
  vbcFailed: boolean;
  /** The furthest MiXCR step's progress line, without the progress prefix. */
  mixcrProgress?: string;
};

/**
 * The progress text of one sample. Once MiXCR has written the qc result, clone export and the
 * VBC step still run, tracked block-wide, since the by-clone-key aggregation spans all samples.
 */
export function sampleProgress(s: SampleState): string {
  if (s.blockErrored) {
    if ((s.started && !s.mixcrDone) || s.vbcFailed) return "Error";
    if (s.mixcrDone) return "Stopped";
  }
  if (!s.mixcrDone) {
    if (!s.started) return s.blockRunning ? "Queued" : "Not started";
    return s.mixcrProgress ?? "Running";
  }
  return s.blockRunning ? "Processing clonotypes" : "Done";
}
