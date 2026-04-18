import { useCallback, useRef, useState } from "react";

import { useUpload } from "../hooks/useUpload";

interface Props {
  onUploadStarted: (jobId: string, filename: string) => void;
  onError: (message: string) => void;
}

export function UploadZone({ onUploadStarted, onError }: Props) {
  const { upload, isUploading, progress, error } = useUpload();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      try {
        const res = await upload(file);
        onUploadStarted(res.job_id, res.filename);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Upload failed";
        onError(message);
      }
    },
    [upload, onUploadStarted, onError],
  );

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setDragOver(false);
      const file = event.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const onChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file) handleFile(file);
      event.target.value = "";
    },
    [handleFile],
  );

  return (
    <section className="mt-8">
      <div className="grid gap-8 lg:grid-cols-[1.6fr_1fr] lg:items-center">
        <div>
          <h2 className="text-3xl font-semibold text-white sm:text-4xl">
            Analyze drone footage in minutes
          </h2>
          <p className="mt-3 max-w-xl text-base text-slate-300">
            Drop in an aerial video, and our pipeline detects, tracks, and counts unique vehicles
            using YOLOv8 + ByteTrack. Get a downloadable CSV/XLSX report when it&apos;s done.
          </p>
          <ul className="mt-6 grid grid-cols-1 gap-3 text-sm text-slate-300 sm:grid-cols-2">
            {[
              "Real-time bounding-box preview",
              "Robust against stops & occlusions",
              "CSV + XLSX automated reports",
              "Up to 500 MB MP4 / MOV / AVI / MKV",
            ].map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-brand-500" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={`glass-card group flex min-h-[260px] flex-col items-center justify-center p-8 text-center transition ${
            dragOver ? "border-brand-500/60 bg-brand-500/10" : ""
          }`}
        >
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600/20 text-2xl text-brand-200">
            ⬆
          </div>
          <p className="text-base font-semibold text-white">
            Drag &amp; drop a drone video here
          </p>
          <p className="mt-1 text-sm text-slate-400">
            or browse your computer (MP4 / MOV / AVI / MKV / WebM)
          </p>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={isUploading}
            className="btn-primary mt-5"
          >
            {isUploading ? "Uploading..." : "Select video"}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept="video/*,.mp4,.mov,.avi,.mkv,.webm"
            className="hidden"
            onChange={onChange}
          />

          {isUploading && (
            <div className="mt-6 w-full">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Uploading...</span>
                <span>{progress}%</span>
              </div>
              <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full bg-brand-500 transition-[width] duration-150"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {error && !isUploading && (
            <p className="mt-4 text-sm text-rose-300">{error}</p>
          )}
        </div>
      </div>
    </section>
  );
}
