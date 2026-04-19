import type {
  JobResultResponse,
  JobStatusResponse,
  UploadResponse,
} from "../types";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

if (import.meta.env.PROD) {
  const bad =
    API_BASE.includes("localhost") ||
    API_BASE.includes("127.0.0.1") ||
    API_BASE.startsWith("http://127.");
  if (bad) {
    console.error(
      "[Smart Drone Traffic Analyzer] Misconfiguration: VITE_API_URL points at this machine (localhost), " +
        "but the app is running on the public web. Set VITE_API_URL in Vercel to your real API HTTPS URL " +
        "(e.g. https://your-api.onrender.com), then redeploy. Current value:",
      API_BASE || "(empty)",
    );
  }
}

function buildUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function parseError(res: Response): Promise<never> {
  let message = `Request failed with status ${res.status}`;
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data?.detail) && data.detail[0]?.msg) {
      message = data.detail.map((d: { msg: string }) => d.msg).join(", ");
    }
  } catch {
    /* no body */
  }
  throw new ApiError(res.status, message);
}

export interface UploadOptions {
  onProgress?: (pct: number) => void;
  signal?: AbortSignal;
}

export function uploadVideo(file: File, opts: UploadOptions = {}): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);

    xhr.open("POST", buildUrl("/api/upload"));
    xhr.responseType = "json";

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && opts.onProgress) {
        opts.onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response as UploadResponse);
      } else {
        const detail =
          (xhr.response && (xhr.response.detail as string)) ||
          `Upload failed (${xhr.status})`;
        reject(new ApiError(xhr.status, detail));
      }
    };

    xhr.onerror = () => reject(new ApiError(0, "Network error during upload"));
    xhr.onabort = () => reject(new ApiError(0, "Upload cancelled"));

    if (opts.signal) {
      opts.signal.addEventListener("abort", () => xhr.abort());
    }

    xhr.send(form);
  });
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(buildUrl(`/api/job/${jobId}/status`));
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function getJobResult(jobId: string): Promise<JobResultResponse> {
  const res = await fetch(buildUrl(`/api/job/${jobId}/result`));
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function cancelJob(jobId: string): Promise<void> {
  const res = await fetch(buildUrl(`/api/job/${jobId}`), { method: "DELETE" });
  if (!res.ok && res.status !== 404) await parseError(res);
}

export function reportUrl(jobId: string, kind: "csv" | "xlsx"): string {
  return buildUrl(`/api/report/${jobId}/${kind}`);
}

export function wsUrl(jobId: string): string {
  if (API_BASE) {
    return `${API_BASE.replace(/^http/, "ws")}/api/ws/${jobId}`;
  }
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/api/ws/${jobId}`;
}
