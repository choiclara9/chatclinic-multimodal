"use client";

import { type ReactNode, type RefObject } from "react";
import IgvBrowser from "./IgvBrowser";

type StudioRendererBuilderArgs = {
  apiBase: string;
  analysis: any;
  rawQcAnalysis: any;
  summaryStatsAnalysis: any;
  prsPrepResultForStudio: any;
  qqmanResultForStudio: any;
  samtoolsResultForStudio: any;
  snpeffResultForStudio: any;
  plinkResultForStudio: any;
  liftoverResultForStudio: any;
  ldblockshowResultForStudio: any;
  summaryStatsGridRows: Array<Record<string, string>>;
  summaryStatsRowsLoading: boolean;
  summaryStatsHasMore: boolean;
  summaryStatsGridRef: RefObject<HTMLDivElement | null>;
  handleSummaryStatsGridScroll: (event: any) => void;
  loadMoreSummaryStatsRows: () => Promise<void>;
  candidateVariants: any[];
  searchedAnnotations: any[];
  setSelectedAnnotationIndex: (index: number) => void;
  setActiveStudioView: (view: any) => void;
  buildAcmgHints: (item: any) => string[];
  annotationScope: string;
  annotationLimit: string;
  qcMetrics: any;
  clinicalCoverage: Array<{ label: string; detail: string }>;
  plinkConfig: any;
  setPlinkConfig: (updater: any) => void;
  plinkCommandPreview: string;
  handleRunPlink: () => Promise<void>;
  plinkRunning: boolean;
  activeSource: any;
  attachedFile: File | null;
  filteringSummary: Array<{ label: string; detail: string }>;
  annotationSearch: string;
  setAnnotationSearch: (value: string) => void;
  symbolicAnnotations: any[];
  rohCandidates: { segments: any[] };
  recessiveShortlist: any[];
  clinvarCounts: Array<{ label: string; count: number }>;
  consequenceCounts: Array<{ label: string; count: number }>;
  geneCounts: Array<{ label: string; count: number }>;
  safeSelectedIndex: number;
  selectedAnnotation: any;
  components: {
    StudioMetricGrid: any;
    StudioPreviewTable: any;
    WarningListCard: any;
    ArtifactLinksRow: any;
    StudioSimpleList: any;
    DistributionList: any;
    VariantTable: any;
    MetricTile: any;
    ReferenceListCard: any;
    AnnotationDetailCard: any;
  };
  helpers: {
    formatPercent: (value?: number | null) => string;
    formatNumber: (value?: number | null) => string;
    summarizeLabel: (value?: string | null, fallback?: string) => string;
  };
};

export function buildStudioRendererRegistry({
  apiBase,
  analysis,
  rawQcAnalysis,
  summaryStatsAnalysis,
  prsPrepResultForStudio,
  qqmanResultForStudio,
  samtoolsResultForStudio,
  snpeffResultForStudio,
  plinkResultForStudio,
  liftoverResultForStudio,
  ldblockshowResultForStudio,
  summaryStatsGridRows,
  summaryStatsRowsLoading,
  summaryStatsHasMore,
  summaryStatsGridRef,
  handleSummaryStatsGridScroll,
  loadMoreSummaryStatsRows,
  candidateVariants,
  searchedAnnotations,
  setSelectedAnnotationIndex,
  setActiveStudioView,
  buildAcmgHints,
  annotationScope,
  annotationLimit,
  qcMetrics,
  clinicalCoverage,
  plinkConfig,
  setPlinkConfig,
  plinkCommandPreview,
  handleRunPlink,
  plinkRunning,
  activeSource,
  attachedFile,
  filteringSummary,
  annotationSearch,
  setAnnotationSearch,
  symbolicAnnotations,
  rohCandidates,
  recessiveShortlist,
  clinvarCounts,
  consequenceCounts,
  geneCounts,
  safeSelectedIndex,
  selectedAnnotation,
  components,
  helpers,
}: StudioRendererBuilderArgs): Partial<Record<string, () => ReactNode>> {
  const {
    StudioMetricGrid,
    StudioPreviewTable,
    WarningListCard,
    ArtifactLinksRow,
    StudioSimpleList,
    DistributionList,
    VariantTable,
    MetricTile,
    ReferenceListCard,
    AnnotationDetailCard,
  } = components;
  const { formatPercent, formatNumber, summarizeLabel } = helpers;

  return {
    rawqc: () =>
      rawQcAnalysis ? (
        <section className="notebookPanel studioCanvasPanel">
          <div className="notebookHeader"><h2>FastQC Review</h2></div>
          <div className="studioCanvasBody">
            <StudioMetricGrid
              items={[
                { label: "Total sequences", value: rawQcAnalysis.facts.total_sequences != null ? String(rawQcAnalysis.facts.total_sequences) : "n/a", tone: "good" },
                { label: "Sequence length", value: rawQcAnalysis.facts.sequence_length ?? "n/a", tone: "neutral" },
                { label: "%GC", value: rawQcAnalysis.facts.gc_content != null ? `${rawQcAnalysis.facts.gc_content.toFixed(1)}%` : "n/a", tone: "neutral" },
                { label: "Encoding", value: rawQcAnalysis.facts.encoding ?? "n/a", tone: "neutral" },
              ]}
            />
            <div className="resultList">
              {rawQcAnalysis.modules.map((module: any) => (
                <article key={module.name} className="miniCard">
                  <h3>{module.name}</h3>
                  <p>Status: {module.status}</p>
                  {module.detail ? <p>{module.detail}</p> : null}
                </article>
              ))}
            </div>
            <ArtifactLinksRow
              items={[
                ...(rawQcAnalysis.report_html_path ? [{ label: "Open HTML report", href: `${apiBase.replace(/\/$/, "")}/api/v1/raw-qc/report?path=${encodeURIComponent(rawQcAnalysis.report_html_path)}` }] : []),
                ...(rawQcAnalysis.report_zip_path ? [{ label: "Download ZIP", href: `${apiBase.replace(/\/$/, "")}/api/v1/raw-qc/report?path=${encodeURIComponent(rawQcAnalysis.report_zip_path)}` }] : []),
              ]}
            />
          </div>
        </section>
      ) : null,
    sumstats: () =>
      summaryStatsAnalysis ? (
        <section className="notebookPanel studioCanvasPanel">
          <div className="notebookHeader"><h2>Summary Stats Review</h2></div>
          <div className="studioCanvasBody">
            <StudioMetricGrid
              items={[
                { label: "Rows", value: String(summaryStatsAnalysis.row_count), tone: "good" },
                { label: "Columns", value: String(summaryStatsAnalysis.detected_columns.length) },
                { label: "Build", value: summaryStatsAnalysis.genome_build },
                { label: "Trait", value: summaryStatsAnalysis.trait_type },
                { label: "Delimiter", value: summaryStatsAnalysis.delimiter },
                { label: "Warnings", value: String(summaryStatsAnalysis.warnings.length) },
              ]}
            />
            <div className="resultSectionSplit">
              <article className="miniCard">
                <h3>Detected columns</h3>
                <ul className="hintList">
                  {summaryStatsAnalysis.detected_columns.map((column: string) => <li key={column}>{column}</li>)}
                </ul>
              </article>
              <article className="miniCard">
                <h3>Auto-mapped fields</h3>
                <ul className="hintList">
                  {Object.entries(summaryStatsAnalysis.mapped_fields).map(([field, value]) => (
                    <li key={field}><strong>{field}</strong>: {(value as string) || "not detected"}</li>
                  ))}
                </ul>
              </article>
            </div>
            <article className="miniCard">
              <h3>Preview grid</h3>
              <p className="summaryStatsGridMeta">Showing {summaryStatsGridRows.length} of {summaryStatsAnalysis.row_count} rows</p>
              <div ref={summaryStatsGridRef} onScroll={handleSummaryStatsGridScroll}>
                <StudioPreviewTable
                  columns={summaryStatsAnalysis.detected_columns}
                  rows={summaryStatsGridRows}
                  rowHeaderLabel="#"
                  footer={
                    <>
                      {summaryStatsRowsLoading ? <div className="summaryStatsGridFooter">Loading more rows...</div> : null}
                      {!summaryStatsRowsLoading && summaryStatsHasMore ? (
                        <div className="summaryStatsGridFooter">
                          <button type="button" className="sourceAddButton summaryStatsLoadMoreButton" onClick={() => void loadMoreSummaryStatsRows()}>
                            Load more rows
                          </button>
                        </div>
                      ) : null}
                      {!summaryStatsHasMore && summaryStatsGridRows.length ? <div className="summaryStatsGridFooter">All loaded rows are shown.</div> : null}
                    </>
                  }
                />
              </div>
            </article>
            <WarningListCard warnings={summaryStatsAnalysis.warnings} />
          </div>
        </section>
      ) : null,
    samtools: () =>
      rawQcAnalysis || samtoolsResultForStudio ? (
        <section className="notebookPanel studioCanvasPanel">
          <div className="notebookHeader"><h2>Samtools Review</h2></div>
          <div className="studioCanvasBody">
            {samtoolsResultForStudio ? (
              <>
                <StudioMetricGrid
                  items={[
                    { label: "File kind", value: samtoolsResultForStudio.file_kind, tone: "good" },
                    { label: "Total reads", value: samtoolsResultForStudio.total_reads != null ? String(samtoolsResultForStudio.total_reads) : "n/a" },
                    { label: "Mapped", value: samtoolsResultForStudio.mapped_reads != null ? `${samtoolsResultForStudio.mapped_reads}${samtoolsResultForStudio.mapped_rate != null ? ` (${samtoolsResultForStudio.mapped_rate.toFixed(2)}%)` : ""}` : "n/a", tone: "good" },
                    { label: "Properly paired", value: samtoolsResultForStudio.properly_paired_reads != null ? `${samtoolsResultForStudio.properly_paired_reads}${samtoolsResultForStudio.properly_paired_rate != null ? ` (${samtoolsResultForStudio.properly_paired_rate.toFixed(2)}%)` : ""}` : "n/a" },
                    { label: "Quickcheck", value: samtoolsResultForStudio.quickcheck_ok ? "PASS" : "Issue detected", tone: samtoolsResultForStudio.quickcheck_ok ? "good" : "warn" },
                    { label: "Index", value: samtoolsResultForStudio.index_path ? "Created / available" : "n/a" },
                  ]}
                />
                <div className="resultSectionSplit">
                  <article className="miniCard">
                    <h3>samtools stats highlights</h3>
                    <StudioSimpleList items={samtoolsResultForStudio.stats_highlights.map((item: any) => ({ label: item.label, detail: item.value }))} emptyLabel="No samtools stats highlights are available." />
                  </article>
                  <article className="miniCard">
                    <h3>idxstats preview</h3>
                    <StudioSimpleList items={samtoolsResultForStudio.idxstats_rows.map((row: any) => ({ label: row.contig, detail: `mapped ${row.mapped} | unmapped ${row.unmapped} | length ${row.length_bp}` }))} emptyLabel="No idxstats preview rows are available." />
                  </article>
                </div>
                <WarningListCard warnings={samtoolsResultForStudio.warnings} />
              </>
            ) : <p className="emptyState">No samtools result is available for the current raw-QC session.</p>}
          </div>
        </section>
      ) : null,
    prs_prep: () =>
      prsPrepResultForStudio ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>PRS Prep Review</h2></div><div className="studioCanvasBody"><div className="resultMetricGrid"><MetricTile label="Inferred build" value={prsPrepResultForStudio.build_check.inferred_build} tone="good" /><MetricTile label="Build confidence" value={prsPrepResultForStudio.build_check.build_confidence} tone="neutral" /><MetricTile label="Effect size" value={prsPrepResultForStudio.harmonization.effect_size_kind} tone="neutral" /><MetricTile label="Ready rows" value={String(prsPrepResultForStudio.kept_rows)} tone={prsPrepResultForStudio.kept_rows > 0 ? "good" : "warn"} /><MetricTile label="Dropped rows" value={String(prsPrepResultForStudio.dropped_rows)} tone="neutral" /><MetricTile label="Score file" value={prsPrepResultForStudio.score_file_ready ? "ready" : "not ready"} tone={prsPrepResultForStudio.score_file_ready ? "good" : "warn"} /></div><div className="resultSectionSplit"><article className="miniCard"><h3>Build check</h3><ul className="hintList"><li><strong>Source build</strong>: {prsPrepResultForStudio.build_check.source_build}</li><li><strong>Target build</strong>: {prsPrepResultForStudio.build_check.target_build}</li><li><strong>Build match</strong>: {prsPrepResultForStudio.build_check.build_match == null ? "undetermined" : prsPrepResultForStudio.build_check.build_match ? "yes" : "no"}</li></ul></article><article className="miniCard"><h3>Harmonization</h3><ul className="hintList"><li><strong>Required fields present</strong>: {prsPrepResultForStudio.harmonization.required_fields_present ? "yes" : "no"}</li><li><strong>Preview rows harmonizable</strong>: {prsPrepResultForStudio.harmonization.harmonizable_preview_rows}</li><li><strong>Ambiguous SNPs</strong>: {prsPrepResultForStudio.harmonization.ambiguous_snp_count}</li>{prsPrepResultForStudio.harmonization.missing_fields.length ? <li><strong>Missing fields</strong>: {prsPrepResultForStudio.harmonization.missing_fields.join(", ")}</li> : null}</ul></article></div><article className="miniCard"><h3>PLINK score-file preview</h3><p className="summaryStatsGridMeta">Columns: {prsPrepResultForStudio.score_file_columns.join(", ") || "ID, A1, BETA"}</p><div className="variantTableWrap summaryStatsTableWrap"><table className="variantTable summaryStatsTable"><thead><tr>{prsPrepResultForStudio.score_file_columns.map((column: string) => <th key={column}>{column}</th>)}</tr></thead><tbody>{prsPrepResultForStudio.score_file_preview_rows.map((row: any, index: number) => <tr key={`prs-prep-preview-${index}`}>{prsPrepResultForStudio.score_file_columns.map((column: string) => <td key={`${index}-${column}`}>{row[column] || ""}</td>)}</tr>)}</tbody></table></div><ArtifactLinksRow items={prsPrepResultForStudio.score_file_path ? [{ label: "Open output", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(prsPrepResultForStudio.score_file_path)}` }] : []} /></article><WarningListCard warnings={[...prsPrepResultForStudio.build_check.warnings, ...prsPrepResultForStudio.harmonization.warnings]} /></div></section>
      ) : null,
    qqman: () =>
      qqmanResultForStudio ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>qqman Plots</h2></div><div className="studioCanvasBody"><StudioMetricGrid items={[{ label: "Tool", value: qqmanResultForStudio.tool, tone: "good" }, { label: "Artifacts", value: String(qqmanResultForStudio.artifacts.length) }, { label: "Warnings", value: String(qqmanResultForStudio.warnings.length) }]} /><div className="resultList"><article className="resultListItem resultListStatic"><strong>Command preview</strong><pre className="codeBlock">{qqmanResultForStudio.command_preview}</pre></article></div><div className="resultSectionSplit">{qqmanResultForStudio.artifacts.map((artifact: any) => <article key={artifact.api_path} className="miniCard"><h3>{artifact.title}</h3><img src={`${apiBase.replace(/\/$/, "")}${artifact.api_path}`} alt={artifact.title} className="plotPreviewImage" /><p className="resultNote">{artifact.note}</p><div className="resultActionRow"><a className="sourceAddButton" href={`${apiBase.replace(/\/$/, "")}${artifact.api_path}`} target="_blank" rel="noreferrer">Open image</a></div></article>)}</div><WarningListCard warnings={qqmanResultForStudio.warnings} /></div></section>
      ) : null,
    provenance: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>Analysis Provenance</h2></div><div className="studioCanvasBody"><StudioMetricGrid items={[{ label: "Annotation scope", value: annotationScope }, { label: "Annotation limit", value: annotationScope === "all" ? annotationLimit || "n/a" : "representative" }, { label: "References", value: String(analysis.references.length) }, { label: "Annotations", value: String(analysis.annotations.length) }]} /><div className="resultSectionSplit"><article className="miniCard"><h3>Tool chain</h3><ul className="hintList"><li>`pysam` for VCF parsing, file summary, and QC metrics</li><li>`Ensembl VEP REST` for consequence, transcript, HGVS, and protein fields</li><li>`ClinVar / NCBI refsnp` for clinical significance and condition labels</li><li>`gnomAD` frequency joins for population rarity context</li><li>`OpenAI` models for workflow intake and grounded narrative explanation</li></ul></article><article className="miniCard"><h3>Current run policy</h3><ul className="hintList"><li>Filtering tools such as `bcftools` and `GATK` are available but were not automatically applied in this summary-first run.</li><li>Representative annotation is the default unless the user explicitly requests a wider range.</li><li>Studio cards are derived from the current annotated subset, not from a separate hidden analysis branch.</li></ul></article></div></div></section>
      ) : null,
    qc: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>QC Summary</h2></div><div className="studioCanvasBody"><StudioMetricGrid items={[{ label: "PASS rate", value: formatPercent(qcMetrics?.pass_rate), tone: "good" }, { label: "Ti/Tv", value: formatNumber(qcMetrics?.transition_transversion_ratio) }, { label: "Missing GT", value: formatPercent(qcMetrics?.missing_gt_rate), tone: "warn" }, { label: "Het/HomAlt", value: formatNumber(qcMetrics?.het_hom_alt_ratio) }, { label: "Multi-allelic", value: formatPercent(qcMetrics?.multi_allelic_rate) }, { label: "Symbolic ALT", value: formatPercent(qcMetrics?.symbolic_alt_rate) }, { label: "SNV fraction", value: formatPercent(qcMetrics?.snv_fraction), tone: "good" }, { label: "Indel fraction", value: formatPercent(qcMetrics?.indel_fraction) }]} /><div className="resultSectionSplit"><article className="miniCard"><h3>Genotype composition</h3><DistributionList items={Object.entries(analysis.facts.genotype_counts).map(([label, count]) => ({ label, count: count as number })).sort((left: any, right: any) => right.count - left.count)} emptyLabel="No genotype counts are available." /></article><article className="miniCard"><h3>Variant classes</h3><DistributionList items={Object.entries(analysis.facts.variant_types).map(([label, count]) => ({ label, count: count as number })).sort((left: any, right: any) => right.count - left.count)} emptyLabel="No variant class counts are available." /></article></div></div></section>
      ) : null,
    coverage: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>Clinical Annotation Coverage</h2></div><div className="studioCanvasBody"><StudioSimpleList items={clinicalCoverage.map((item) => ({ label: item.label, detail: item.detail }))} emptyLabel="No clinical coverage summary is available." /></div></section>
      ) : null,
    snpeff: () =>
      analysis || snpeffResultForStudio ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>SnpEff Review</h2></div><div className="studioCanvasBody">{snpeffResultForStudio ? <><StudioMetricGrid items={[{ label: "Genome DB", value: snpeffResultForStudio.genome, tone: "good" }, { label: "Preview rows", value: String(snpeffResultForStudio.parsed_records.length) }, { label: "Tool", value: snpeffResultForStudio.tool }]} /><div className="resultList">{snpeffResultForStudio.parsed_records.map((record: any, index: number) => <article key={`${record.contig}-${record.pos_1based}-${record.alt}-${index}`} className="resultListItem resultListStatic"><strong>{record.contig}:{record.pos_1based} {record.ref}&gt;{record.alt}</strong><span>{record.ann.length ? record.ann.slice(0, 2).map((ann: any) => `${ann.gene_name || "Unknown"} | ${ann.annotation} | ${ann.impact} | ${ann.hgvs_c || "."} | ${ann.hgvs_p || "."}`).join(" || ") : "No parsed ANN entries"}</span></article>)}</div><ArtifactLinksRow items={[{ label: "Open annotated VCF", href: `file://${snpeffResultForStudio.output_path}` }]} /></> : <p className="emptyState">No auxiliary SnpEff result is available for the current analysis.</p>}</div></section>
      ) : null,
    plink: () =>
      analysis || plinkResultForStudio ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>PLINK</h2></div><div className="studioCanvasBody"><div className="resultMetricGrid"><MetricTile label="Mode" value={plinkConfig.mode === "score" ? "Score" : "QC"} tone="good" /><MetricTile label="Source" value={analysis?.facts.file_name ?? activeSource?.file_name ?? attachedFile?.name ?? "n/a"} tone="neutral" /><MetricTile label="Existing result" value={plinkResultForStudio ? "Available" : "Not run yet"} tone={plinkResultForStudio ? "good" : "neutral"} /><MetricTile label="Runner" value={plinkRunning ? "Running" : "Ready"} tone={plinkRunning ? "warn" : "good"} /></div><div className="resultList"><article className="resultListItem resultListStatic"><strong>Run configuration</strong><div className="annotationMetaGrid"><label className="field compactField"><span>Mode</span><select value={plinkConfig.mode} onChange={(event) => setPlinkConfig((current: any) => ({ ...current, mode: event.target.value }))}><option value="qc">qc</option><option value="score">score</option></select></label><label className="field compactField"><span>Output prefix</span><input type="text" value={plinkConfig.outputPrefix} onChange={(event) => setPlinkConfig((current: any) => ({ ...current, outputPrefix: event.target.value }))} /></label><label className="field compactField"><span>Frequency summary</span><input type="checkbox" checked={plinkConfig.runFreq} disabled={plinkConfig.mode === "score"} onChange={(event) => setPlinkConfig((current: any) => ({ ...current, runFreq: event.target.checked }))} /></label><label className="field compactField"><span>Missingness summary</span><input type="checkbox" checked={plinkConfig.runMissing} disabled={plinkConfig.mode === "score"} onChange={(event) => setPlinkConfig((current: any) => ({ ...current, runMissing: event.target.checked }))} /></label><label className="field compactField"><span>Hardy-Weinberg summary</span><input type="checkbox" checked={plinkConfig.runHardy} disabled={plinkConfig.mode === "score"} onChange={(event) => setPlinkConfig((current: any) => ({ ...current, runHardy: event.target.checked }))} /></label><label className="field compactField"><span>Allow extra chr labels</span><input type="checkbox" checked={plinkConfig.allowExtraChr} onChange={(event) => setPlinkConfig((current: any) => ({ ...current, allowExtraChr: event.target.checked }))} /></label></div>{plinkConfig.mode === "score" ? <p className="resultNote">Score mode uses the latest PRS prep score file. Run <code>@skill prs_prep</code> on a summary-statistics source first, then upload a target genotype VCF and run <code>@plink score</code>.</p> : null}</article><article className="resultListItem resultListStatic"><strong>Command preview</strong><pre className="codeBlock">{plinkCommandPreview}</pre></article></div><div className="resultActionRow"><button className="sourceAddButton" type="button" onClick={() => void handleRunPlink()} disabled={plinkRunning || !(analysis?.source_vcf_path || (activeSource?.source_type === "vcf" ? activeSource.source_path : null))}>{plinkRunning ? "Running PLINK..." : "Run PLINK"}</button></div>{plinkResultForStudio ? plinkResultForStudio.mode === "score" ? <><div className="resultMetricGrid"><MetricTile label="Samples scored" value={plinkResultForStudio.sample_count != null ? String(plinkResultForStudio.sample_count) : String(plinkResultForStudio.score_rows.length)} tone="good" /><MetricTile label="Mean score" value={plinkResultForStudio.score_mean != null ? plinkResultForStudio.score_mean.toFixed(4) : "n/a"} tone="neutral" /><MetricTile label="Min score" value={plinkResultForStudio.score_min != null ? plinkResultForStudio.score_min.toFixed(4) : "n/a"} tone="neutral" /><MetricTile label="Max score" value={plinkResultForStudio.score_max != null ? plinkResultForStudio.score_max.toFixed(4) : "n/a"} tone="neutral" /><MetricTile label="Preview rows" value={String(plinkResultForStudio.score_rows.length)} tone="good" /><MetricTile label="Warnings" value={String(plinkResultForStudio.warnings.length)} tone="neutral" /></div><div className="resultList"><article className="resultListItem resultListStatic"><strong>PRS score inputs</strong><span>Target genotype: {plinkResultForStudio.input_path}</span><span>Score file: {plinkResultForStudio.score_file_path || "n/a"}</span></article>{plinkResultForStudio.score_rows.slice(0, 10).map((row: any, index: number) => <article key={`plink-score-${row.sample_id}-${index}`} className="resultListItem resultListStatic"><strong>{row.sample_id}</strong><span>allele ct {row.allele_ct != null ? row.allele_ct.toFixed(2) : "n/a"} | dosage sum {row.named_allele_dosage_sum != null ? row.named_allele_dosage_sum.toFixed(2) : "n/a"} | score {row.score_sum != null ? row.score_sum.toFixed(4) : "n/a"}</span></article>)}{plinkResultForStudio.warnings.map((warning: string, index: number) => <article key={`plink-warning-${index}`} className="resultListItem resultListStatic"><strong>Warning {index + 1}</strong><span>{warning}</span></article>)}</div><ArtifactLinksRow items={[...(plinkResultForStudio.score_output_path ? [{ label: "Open output", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(plinkResultForStudio.score_output_path)}` }] : []), ...(plinkResultForStudio.log_path ? [{ label: "Open log", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(plinkResultForStudio.log_path)}` }] : [])]} /></> : <><div className="resultMetricGrid"><MetricTile label="Samples" value={plinkResultForStudio.sample_count != null ? String(plinkResultForStudio.sample_count) : "n/a"} tone="neutral" /><MetricTile label="Variants" value={plinkResultForStudio.variant_count != null ? String(plinkResultForStudio.variant_count) : "n/a"} tone="neutral" /><MetricTile label="Freq rows" value={String(plinkResultForStudio.freq_rows.length)} tone="good" /><MetricTile label="Missing rows" value={String(plinkResultForStudio.missing_rows.length)} tone="good" /><MetricTile label="Hardy rows" value={String(plinkResultForStudio.hardy_rows.length)} tone="good" /><MetricTile label="Warnings" value={String(plinkResultForStudio.warnings.length)} tone="neutral" /></div><div className="resultList">{plinkResultForStudio.freq_rows.slice(0, 5).map((row: any, index: number) => <article key={`plink-freq-${row.variant_id}-${index}`} className="resultListItem resultListStatic"><strong>{row.chrom}:{row.variant_id}</strong><span>{row.ref_allele}&gt;{row.alt_allele} | AF {row.alt_freq != null ? row.alt_freq.toFixed(4) : "n/a"} | OBS {row.observation_count ?? "n/a"}</span></article>)}{plinkResultForStudio.missing_rows.slice(0, 3).map((row: any, index: number) => <article key={`plink-missing-${row.sample_id}-${index}`} className="resultListItem resultListStatic"><strong>Missingness {row.sample_id}</strong><span>{row.missing_genotype_count} missing / {row.observation_count} obs | rate {(row.missing_rate * 100).toFixed(2)}%</span></article>)}{plinkResultForStudio.hardy_rows.slice(0, 5).map((row: any, index: number) => <article key={`plink-hardy-${row.variant_id}-${index}`} className="resultListItem resultListStatic"><strong>Hardy {row.chrom}:{row.variant_id}</strong><span>obs het {row.observed_hets ?? "n/a"} | exp het {row.expected_hets != null ? row.expected_hets.toFixed(2) : "n/a"} | p {row.p_value != null ? row.p_value.toExponential(3) : "n/a"}</span></article>)}{plinkResultForStudio.warnings.map((warning: string, index: number) => <article key={`plink-warning-${index}`} className="resultListItem resultListStatic"><strong>Warning {index + 1}</strong><span>{warning}</span></article>)}</div><ArtifactLinksRow items={[...(plinkResultForStudio.freq_path ? [{ label: "Open afreq", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(plinkResultForStudio.freq_path)}` }] : []), ...(plinkResultForStudio.missing_path ? [{ label: "Open smiss", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(plinkResultForStudio.missing_path)}` }] : []), ...(plinkResultForStudio.hardy_path ? [{ label: "Open hardy", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(plinkResultForStudio.hardy_path)}` }] : []), ...(plinkResultForStudio.log_path ? [{ label: "Open log", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(plinkResultForStudio.log_path)}` }] : [])]} /></> : <p className="emptyState">No PLINK result is available yet. Configure the run and execute it from this card.</p>}</div></section>
      ) : null,
    liftover: () =>
      analysis || liftoverResultForStudio ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>LiftOver Review</h2></div><div className="studioCanvasBody">{liftoverResultForStudio ? <><StudioMetricGrid items={[{ label: "Source build", value: liftoverResultForStudio.source_build ?? "unknown", tone: "neutral" }, { label: "Target build", value: liftoverResultForStudio.target_build ?? "unknown", tone: "good" }, { label: "Lifted records", value: String(liftoverResultForStudio.lifted_record_count ?? 0), tone: "good" }, { label: "Rejected records", value: String(liftoverResultForStudio.rejected_record_count ?? 0), tone: "neutral" }, { label: "Warnings", value: String(liftoverResultForStudio.warnings.length), tone: "neutral" }, { label: "Tool", value: liftoverResultForStudio.tool, tone: "neutral" }]} /><div className="resultList">{liftoverResultForStudio.parsed_records.length ? liftoverResultForStudio.parsed_records.map((record: any, index: number) => <article key={`${record.contig}-${record.pos_1based}-${index}`} className="resultListItem resultListStatic"><strong>{record.contig}:{record.pos_1based} {record.ref}&gt;{record.alts.join(",")}</strong><span>Lifted preview record</span></article>) : <p className="emptyState">No lifted preview records are available for this result.</p>}{liftoverResultForStudio.warnings.length ? liftoverResultForStudio.warnings.map((warning: string, index: number) => <article key={`liftover-warning-${index}`} className="resultListItem resultListStatic"><strong>Warning {index + 1}</strong><span>{warning}</span></article>) : null}</div><ArtifactLinksRow items={[{ label: "Open lifted VCF", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(liftoverResultForStudio.output_path)}` }, { label: "Open reject VCF", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(liftoverResultForStudio.reject_path)}` }]} /></> : <p className="emptyState">No liftover result is available for the current analysis.</p>}</div></section>
      ) : null,
    ldblockshow: () =>
      analysis || ldblockshowResultForStudio ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>LD Block Review</h2></div><div className="studioCanvasBody">{ldblockshowResultForStudio ? <><StudioMetricGrid items={[{ label: "Region", value: ldblockshowResultForStudio.region, tone: "good" }, { label: "Tried regions", value: String(ldblockshowResultForStudio.attempted_regions?.length ?? 0), tone: "neutral" }, { label: "Site rows", value: String(ldblockshowResultForStudio.site_row_count ?? 0), tone: "neutral" }, { label: "Triangle pairs", value: String(ldblockshowResultForStudio.triangle_pair_count ?? 0), tone: "neutral" }, { label: "Warnings", value: String(ldblockshowResultForStudio.warnings.length), tone: "neutral" }, { label: "Tool", value: ldblockshowResultForStudio.tool, tone: "neutral" }]} /><div className="resultList">{ldblockshowResultForStudio.attempted_regions?.length ? <article className="resultListItem resultListStatic"><strong>Attempted regions</strong><span>{ldblockshowResultForStudio.attempted_regions.join(" -> ")}</span></article> : null}</div><WarningListCard warnings={ldblockshowResultForStudio.warnings} emptyLabel="No LDBlockShow warnings were reported." emptyAsParagraph /><ArtifactLinksRow items={[...(ldblockshowResultForStudio.svg_path ? [{ label: "Open LD SVG", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(ldblockshowResultForStudio.svg_path)}` }] : []), ...(ldblockshowResultForStudio.block_path ? [{ label: "Open block table", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(ldblockshowResultForStudio.block_path)}` }] : []), ...(ldblockshowResultForStudio.site_path ? [{ label: "Open site table", href: `${apiBase.replace(/\/$/, "")}/api/v1/files?path=${encodeURIComponent(ldblockshowResultForStudio.site_path)}` }] : [])]} /></> : <p className="emptyState">No LDBlockShow result is available for the current analysis.</p>}</div></section>
      ) : null,
    candidates: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>Candidate Variants</h2></div><div className="studioCanvasBody"><div className="resultList">{candidateVariants.map(({ item, score, inRoh }: any) => <button type="button" key={`${item.contig}-${item.pos_1based}-${item.rsid}-candidate`} className="resultListItem" onClick={() => { const nextIndex = searchedAnnotations.findIndex((candidate: any) => candidate.contig === item.contig && candidate.pos_1based === item.pos_1based && candidate.rsid === item.rsid); setSelectedAnnotationIndex(nextIndex >= 0 ? nextIndex : 0); setActiveStudioView("annotations"); }}><strong>{item.gene || "Unknown"} | {item.contig}:{item.pos_1based}</strong><span>Score {score} | {summarizeLabel(item.consequence, "Unclassified")} | {summarizeLabel(item.clinical_significance, "Unreviewed")}{inRoh ? " | inside ROH" : ""}{item.cadd_phred != null ? ` | CADD ${item.cadd_phred.toFixed(1)}` : ""}{item.revel_score != null ? ` | REVEL ${item.revel_score.toFixed(3)}` : ""}{" | "}gnomAD {item.gnomad_af || "n/a"}</span></button>)}</div></div></section>
      ) : null,
    acmg: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>ACMG Review</h2></div><div className="studioCanvasBody"><p className="emptyState acmgNote">This is a triage view with ACMG-style evidence hints. It is not a final clinical classification.</p><div className="resultList">{candidateVariants.slice(0, 6).map(({ item }: any) => <article key={`${item.contig}-${item.pos_1based}-${item.rsid}-acmg`} className="resultListItem resultListStatic"><strong>{item.gene || "Unknown"} | {item.rsid || `${item.contig}:${item.pos_1based}`}</strong><span>{summarizeLabel(item.consequence, "Unclassified")} | {summarizeLabel(item.clinical_significance, "Unreviewed")}</span><ul className="hintList">{buildAcmgHints(item).map((hint) => <li key={hint}>{hint}</li>)}</ul></article>)}</div></div></section>
      ) : null,
    table: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>Variant Table</h2><span className="pill">{searchedAnnotations.length} rows</span></div><div className="studioCanvasBody"><StudioSimpleList items={filteringSummary.map((item) => ({ label: item.label, detail: item.detail }))} /><div className="oeAnnotationControls"><label className="field"><span>Search gene / consequence / ClinVar</span><input value={annotationSearch} onChange={(event) => { setAnnotationSearch(event.target.value); setSelectedAnnotationIndex(0); }} placeholder="e.g. PALMD, missense_variant, benign" /></label></div><VariantTable items={searchedAnnotations} onSelect={(item: any) => { const nextIndex = searchedAnnotations.findIndex((candidate: any) => candidate.contig === item.contig && candidate.pos_1based === item.pos_1based && candidate.rsid === item.rsid); setSelectedAnnotationIndex(nextIndex >= 0 ? nextIndex : 0); setActiveStudioView("annotations"); }} /></div></section>
      ) : null,
    symbolic: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>Symbolic ALT Review</h2></div><div className="studioCanvasBody"><p className="emptyState acmgNote">Symbolic ALT records are separated here so they are not over-interpreted as ordinary SNV/indel calls.</p>{symbolicAnnotations.length ? <div className="resultList">{symbolicAnnotations.map((item: any) => <button type="button" key={`${item.contig}-${item.pos_1based}-${item.rsid}-symbolic`} className="resultListItem" onClick={() => { const nextIndex = searchedAnnotations.findIndex((candidate: any) => candidate.contig === item.contig && candidate.pos_1based === item.pos_1based && candidate.rsid === item.rsid); setSelectedAnnotationIndex(nextIndex >= 0 ? nextIndex : 0); setActiveStudioView("annotations"); }}><strong>{item.contig}:{item.pos_1based} | {item.gene || "Unknown"} | {item.alts.join(",")}</strong><span>{summarizeLabel(item.consequence, "Unclassified")} | genotype {item.genotype}</span></button>)}</div> : <p className="emptyState">No symbolic ALT records are present in the current annotated subset.</p>}</div></section>
      ) : null,
    roh: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>ROH / Recessive Review</h2></div><div className="studioCanvasBody"><p className="emptyState acmgNote">This is a homozygous-alt review and ROH-style heuristic from the current annotated subset. A full production workflow should add `bcftools roh` on the complete callset.</p><div className="resultSectionSplit"><article className="miniCard"><h3>ROH-style segments</h3>{rohCandidates.segments.length ? <div className="resultList">{rohCandidates.segments.map((segment: any) => <article key={segment.label} className="resultListItem resultListStatic"><strong>{segment.label}</strong><span>{segment.count} markers | span {segment.spanMb}{segment.quality != null ? ` | quality ${segment.quality.toFixed(1)}` : ""}{segment.sample ? ` | ${segment.sample}` : ""}</span></article>)}</div> : <p className="emptyState">No multi-site homozygous stretches were detected in the current subset.</p>}</article><article className="miniCard"><h3>Recessive-model candidates</h3>{recessiveShortlist.length ? <div className="resultList">{recessiveShortlist.map(({ item, score, inRoh }: any) => <button type="button" key={`${item.contig}-${item.pos_1based}-${item.rsid}-roh`} className="resultListItem" onClick={() => { const nextIndex = searchedAnnotations.findIndex((candidate: any) => candidate.contig === item.contig && candidate.pos_1based === item.pos_1based && candidate.rsid === item.rsid); setSelectedAnnotationIndex(nextIndex >= 0 ? nextIndex : 0); setActiveStudioView("annotations"); }}><strong>{item.gene || "Unknown"} | {item.contig}:{item.pos_1based}</strong><span>score {score} | genotype {item.genotype}{inRoh ? " | inside ROH" : ""}{" | "}{summarizeLabel(item.consequence, "Unclassified")} | gnomAD {item.gnomad_af || "n/a"}</span></button>)}</div> : <p className="emptyState">No homozygous alternate candidates are present in the current annotated subset.</p>}</article></div></div></section>
      ) : null,
    clinvar: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>ClinVar Review</h2></div><div className="studioCanvasBody"><div className="resultSectionSplit"><article className="miniCard"><h3>Clinical significance mix</h3><DistributionList items={clinvarCounts} emptyLabel="No ClinVar-style labels were found." /></article><article className="miniCard"><h3>Representative records</h3><div className="resultList">{analysis.annotations.slice(0, 8).map((item: any) => <button type="button" key={`${item.contig}-${item.pos_1based}-${item.rsid}-clinvar`} className="resultListItem" onClick={() => { const nextIndex = searchedAnnotations.findIndex((candidate: any) => candidate.contig === item.contig && candidate.pos_1based === item.pos_1based && candidate.rsid === item.rsid); setSelectedAnnotationIndex(nextIndex >= 0 ? nextIndex : 0); setActiveStudioView("annotations"); }}><strong>{item.gene || "Unknown"} | {item.rsid || `${item.contig}:${item.pos_1based}`}</strong><span>{summarizeLabel(item.clinical_significance, "Unreviewed")} | {summarizeLabel(item.clinvar_conditions, "No condition")}</span></button>)}</div></article></div></div></section>
      ) : null,
    vep: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>VEP Consequence</h2></div><div className="studioCanvasBody"><div className="resultSectionSplit"><article className="miniCard"><h3>Top consequences</h3><DistributionList items={consequenceCounts} emptyLabel="No consequence labels were found." /></article><article className="miniCard"><h3>Gene burden</h3><DistributionList items={geneCounts} emptyLabel="No gene burden summary is available." /></article></div></div></section>
      ) : null,
    references: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>References</h2></div><div className="studioCanvasBody"><ReferenceListCard items={analysis.references} /></div></section>
      ) : null,
    igv: () =>
      analysis ? (
        <section className="studioCanvasPanel"><IgvBrowser buildGuess={analysis.facts.genome_build_guess ?? null} annotations={searchedAnnotations} selectedIndex={safeSelectedIndex} /></section>
      ) : null,
    annotations: () =>
      analysis ? (
        <section className="notebookPanel studioCanvasPanel"><div className="notebookHeader"><h2>Annotations</h2></div><div className="studioCanvasBody"><div className="oeAnnotationControls"><label className="field"><span>Search gene / consequence / ClinVar</span><input value={annotationSearch} onChange={(event) => { setAnnotationSearch(event.target.value); setSelectedAnnotationIndex(0); }} placeholder="e.g. PALMD, missense_variant, benign" /></label><label className="field"><span>Annotation dropdown</span><select value={safeSelectedIndex} onChange={(event) => setSelectedAnnotationIndex(Number(event.target.value))} disabled={!searchedAnnotations.length}>{searchedAnnotations.length ? searchedAnnotations.map((item: any, index: number) => <option key={`${item.contig}-${item.pos_1based}-${item.rsid}-${index}`} value={index}>{item.gene || "Unknown"} | {item.contig}:{item.pos_1based} | {item.rsid || "no-rsID"} | {item.consequence}</option>) : <option value={0}>No annotations matched the search</option>}</select></label></div>{selectedAnnotation ? <AnnotationDetailCard item={selectedAnnotation} /> : <p className="emptyState">No annotation is available for the current selection.</p>}</div></section>
      ) : null,
  };
}
