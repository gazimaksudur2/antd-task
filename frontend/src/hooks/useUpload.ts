import { useCallback, useRef, useState } from "react";

import { ApiError, uploadVideo } from "../services/api";
import type { UploadResponse } from "../types";

const MAX_BYTES = 500 * 1024 * 1024; // mirror backend default
const ALLOWED_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm"];
const ALLOWED_MIME_PREFIX = "video/";

export interface UseUploadResult {
  upload: (file: File) => Promise<UploadResponse>;
  cancel: () => void;
  isUploading: boolean;
  progress: number;
  error: string | null;
  reset: () => void;
}

function validateFile(file: File): string | null {
  const lowerName = file.name.toLowerCase();
  const extOk = ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
  const mimeOk = file.type === "" || file.type.startsWith(ALLOWED_MIME_PREFIX);
  if (!extOk && !mimeOk) {
    return `Unsupported file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
  }
  if (file.size > MAX_BYTES) {
    const mb = Math.round(file.size / (1024 * 1024));
    return `File is ${mb} MB; maximum allowed is 500 MB`;
  }
  if (file.size === 0) {
    return "File is empty";
  }
  return null;
}

export function useUpload(): UseUploadResult {
  const [isUploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    setProgress(0);
    setError(null);
    setUploading(false);
    abortRef.current = null;
  }, []);

  const upload = useCallback(async (file: File) => {
    const validation = validateFile(file);
    if (validation) {
      setError(validation);
      throw new ApiError(422, validation);
    }
    setError(null);
    setProgress(0);
    setUploading(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const result = await uploadVideo(file, {
        onProgress: setProgress,
        signal: controller.signal,
      });
      return result;
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Upload failed";
      setError(message);
      throw err;
    } finally {
      setUploading(false);
    }
  }, []);

  return { upload, cancel, isUploading, progress, error, reset };
}
