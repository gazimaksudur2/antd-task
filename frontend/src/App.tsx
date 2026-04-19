import { useCallback, useState } from "react";

import { ProcessingView } from "./components/ProcessingView";
import { ReportDownload } from "./components/ReportDownload";
import { SummaryPanel } from "./components/SummaryPanel";
import { useToast } from "./components/ToastProvider";
import { UploadZone } from "./components/UploadZone";
import type { AppPhase, JobSummary } from "./types";

interface CompletedJob {
  jobId: string;
  filename: string;
  summary: JobSummary;
  reportCsvUrl: string;
  reportXlsxUrl: string;
}

interface ActiveJob {
  jobId: string;
  filename: string;
}

export default function App() {
  const [phase, setPhase] = useState<AppPhase>("upload");
  const [activeJob, setActiveJob] = useState<ActiveJob | null>(null);
  const [completed, setCompleted] = useState<CompletedJob | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { push } = useToast();

  const handleUploadStarted = useCallback(
    (jobId: string, filename: string) => {
      setActiveJob({ jobId, filename });
      setPhase("processing");
      push("info", `Processing started for ${filename}`);
    },
    [push],
  );

  const handleProcessingComplete = useCallback(
    (job: CompletedJob) => {
      setCompleted(job);
      setPhase("results");
      push("success", `Detected ${job.summary.total_vehicles} unique vehicles`);
    },
    [push],
  );

  const handleProcessingError = useCallback(
    (message: string) => {
      setErrorMessage(message);
      setPhase("error");
      push("error", message);
    },
    [push],
  );

  const reset = useCallback(() => {
    setActiveJob(null);
    setCompleted(null);
    setErrorMessage(null);
    setPhase("upload");
  }, []);

  return (
    <div className="min-h-full">
      <Header />
      <main className="mx-auto w-full max-w-6xl px-4 pb-24 pt-8 sm:px-6 lg:px-8">
        {phase === "upload" && (
          <UploadZone
            onUploadStarted={handleUploadStarted}
            onError={(msg) => push("error", msg)}
          />
        )}

        {phase === "processing" && activeJob && (
          <ProcessingView
            jobId={activeJob.jobId}
            filename={activeJob.filename}
            onComplete={(summary, csv, xlsx) =>
              handleProcessingComplete({
                jobId: activeJob.jobId,
                filename: activeJob.filename,
                summary,
                reportCsvUrl: csv,
                reportXlsxUrl: xlsx,
              })
            }
            onError={handleProcessingError}
            onCancel={reset}
          />
        )}

        {phase === "results" && completed && (
          <div className="space-y-6">
            <SummaryPanel summary={completed.summary} filename={completed.filename} />
            <ReportDownload
              csvUrl={completed.reportCsvUrl}
              xlsxUrl={completed.reportXlsxUrl}
              onAnalyzeAnother={reset}
            />
          </div>
        )}

        {phase === "error" && (
          <ErrorPanel message={errorMessage ?? "Something went wrong"} onRetry={reset} />
        )}
      </main>

    </div>
  );
}

function Header() {
  return (
    <header className="border-b border-white/5 bg-slate-950/40 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-lg font-bold text-white shadow-lg shadow-brand-900/50">
            D
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white sm:text-xl">
              Smart Drone Traffic Analyzer
            </h1>
            <p className="text-xs text-slate-400 sm:text-sm">
              Upload aerial footage. Get accurate vehicle counts and reports.
            </p>
          </div>
        </div>
        <a
          href="https://github.com/"
          target="_blank"
          rel="noreferrer"
          className="hidden text-sm text-slate-400 transition hover:text-white sm:block"
        >
          Documentation
        </a>
      </div>
    </header>
  );
}

interface ErrorPanelProps {
  message: string;
  onRetry: () => void;
}

function ErrorPanel({ message, onRetry }: ErrorPanelProps) {
  return (
    <section className="glass-card mt-12 p-10 text-center">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-rose-500/15 text-2xl">
        !
      </div>
      <h2 className="text-2xl font-semibold text-white">Processing failed</h2>
      <p className="mx-auto mt-3 max-w-xl text-sm text-slate-300">{message}</p>
      <button type="button" onClick={onRetry} className="btn-primary mt-6">
        Try again
      </button>
    </section>
  );
}
