interface Props {
  csvUrl: string;
  xlsxUrl: string;
  onAnalyzeAnother: () => void;
}

export function ReportDownload({ csvUrl, xlsxUrl, onAnalyzeAnother }: Props) {
  return (
    <section className="glass-card flex flex-col gap-5 p-6 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h3 className="text-lg font-semibold text-white">Download the report</h3>
        <p className="mt-1 text-sm text-slate-400">
          Detailed per-frame detections, line-crossing events, and summary metrics.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <a className="btn-secondary" href={csvUrl} download>
          <DownloadIcon /> CSV
        </a>
        <a className="btn-primary" href={xlsxUrl} download>
          <DownloadIcon /> Excel (.xlsx)
        </a>
        <button type="button" className="btn-secondary" onClick={onAnalyzeAnother}>
          Analyze another video
        </button>
      </div>
    </section>
  );
}

function DownloadIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}
