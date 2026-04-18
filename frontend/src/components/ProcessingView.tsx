import { useEffect, useMemo, useRef } from "react";

import { useJobStream } from "../hooks/useJobStream";
import { cancelJob } from "../services/api";
import type { JobSummary } from "../types";

interface Props {
  jobId: string;
  filename: string;
  onComplete: (summary: JobSummary, csvUrl: string, xlsxUrl: string) => void;
  onError: (message: string) => void;
  onCancel: () => void;
}

export function ProcessingView({ jobId, filename, onComplete, onError, onCancel }: Props) {
  const stream = useJobStream(jobId);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  // Decode incoming JPEG frames onto a canvas for smooth playback.
  useEffect(() => {
    if (!stream.frameDataUrl) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const img = imgRef.current ?? new Image();
    imgRef.current = img;
    img.onload = () => {
      if (canvas.width !== img.naturalWidth || canvas.height !== img.naturalHeight) {
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
      }
      const ctx = canvas.getContext("2d");
      ctx?.drawImage(img, 0, 0);
    };
    img.src = stream.frameDataUrl;
  }, [stream.frameDataUrl]);

  useEffect(() => {
    if (
      stream.status === "complete" &&
      stream.summary &&
      stream.reportCsvUrl &&
      stream.reportXlsxUrl
    ) {
      onComplete(stream.summary, stream.reportCsvUrl, stream.reportXlsxUrl);
    }
  }, [stream.status, stream.summary, stream.reportCsvUrl, stream.reportXlsxUrl, onComplete]);

  useEffect(() => {
    if (stream.status === "error" && stream.error) {
      onError(stream.error);
    }
  }, [stream.status, stream.error, onError]);

  const pct = Math.max(0, Math.min(100, stream.pct));
  const ringStyle = useMemo(
    () => ({
      background: `conic-gradient(rgb(59 130 246) ${pct * 3.6}deg, rgba(255,255,255,0.08) ${pct * 3.6}deg)`,
    }),
    [pct],
  );

  const handleCancel = async () => {
    try {
      await cancelJob(jobId);
    } catch {
      /* swallow — UI already returns home */
    }
    onCancel();
  };

  return (
    <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
      <div className="glass-card overflow-hidden">
        <div className="border-b border-white/5 px-5 py-3 text-sm text-slate-300">
          Processing <span className="font-mono text-white">{filename}</span>
        </div>
        <div className="relative flex aspect-video w-full items-center justify-center bg-black">
          {stream.frameDataUrl ? (
            <canvas
              ref={canvasRef}
              className="h-full w-full object-contain"
              aria-label="Live processed frame preview"
            />
          ) : (
            <div className="flex flex-col items-center gap-3 text-slate-400">
              <div className="h-10 w-10 animate-spin rounded-full border-2 border-white/20 border-t-brand-500" />
              <span className="text-sm">Warming up the model...</span>
            </div>
          )}
          {stream.processed > 0 && stream.total > 0 && (
            <div className="absolute bottom-3 left-3 rounded-md bg-black/60 px-3 py-1 text-xs font-mono text-slate-200">
              frame {stream.processed} / {stream.total}
            </div>
          )}
        </div>
      </div>

      <div className="glass-card flex flex-col items-center gap-6 p-6">
        <div className="text-center">
          <p className="text-xs uppercase tracking-widest text-slate-400">Progress</p>
          <h2 className="mt-1 text-xl font-semibold text-white">Live analysis</h2>
        </div>
        <div
          className="relative flex h-44 w-44 items-center justify-center rounded-full"
          style={ringStyle}
        >
          <div className="flex h-36 w-36 flex-col items-center justify-center rounded-full bg-slate-950">
            <span className="text-3xl font-bold text-white">{pct.toFixed(0)}%</span>
            <span className="mt-1 text-xs uppercase tracking-widest text-slate-400">
              {stream.status === "complete" ? "done" : "processing"}
            </span>
          </div>
        </div>
        <div className="grid w-full grid-cols-2 gap-3 text-center text-sm">
          <Stat label="Frames" value={`${stream.processed}/${stream.total || "?"}`} />
          <Stat label="Status" value={stream.status} />
        </div>
        <button type="button" className="btn-secondary w-full" onClick={handleCancel}>
          Cancel
        </button>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
      <p className="text-xs uppercase tracking-widest text-slate-500">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-white">{value}</p>
    </div>
  );
}
