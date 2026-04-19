export type JobStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "cancelled";

export interface UploadResponse {
  job_id: string;
  filename: string;
  size_bytes: number;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  pct: number;
  message?: string | null;
}

export interface JobSummary {
  total_vehicles: number;
  by_type: Record<string, number>;
  processing_seconds: number;
  frame_count: number;
  fps: number;
  duration_seconds: number;
}

export interface JobResultResponse {
  job_id: string;
  status: JobStatus;
  summary: JobSummary;
  report_csv_url: string;
  report_xlsx_url: string;
}

export type WSMessage =
  | { type: "progress"; pct: number; processed: number; total: number }
  | { type: "frame"; frame_idx: number; data: string }
  | {
      type: "complete";
      summary: JobSummary;
      report_csv_url: string;
      report_xlsx_url: string;
    }
  | { type: "error"; message: string };

export type AppPhase = "upload" | "processing" | "results" | "error";
