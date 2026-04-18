import { useEffect, useRef, useState } from "react";

import { getJobResult, getJobStatus, wsUrl } from "../services/api";
import type { JobSummary, WSMessage } from "../types";

export interface JobStreamState {
  pct: number;
  processed: number;
  total: number;
  frameDataUrl: string | null;
  status: "connecting" | "streaming" | "complete" | "error";
  error: string | null;
  summary: JobSummary | null;
  reportCsvUrl: string | null;
  reportXlsxUrl: string | null;
}

const INITIAL: JobStreamState = {
  pct: 0,
  processed: 0,
  total: 0,
  frameDataUrl: null,
  status: "connecting",
  error: null,
  summary: null,
  reportCsvUrl: null,
  reportXlsxUrl: null,
};

/** Subscribe to a job's progress over WebSocket, with polling fallback. */
export function useJobStream(jobId: string | null): JobStreamState {
  const [state, setState] = useState<JobStreamState>(INITIAL);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    if (!jobId) {
      setState(INITIAL);
      return;
    }

    let cancelled = false;
    setState({ ...INITIAL });

    const startPolling = () => {
      if (pollRef.current) return;
      const tick = async () => {
        try {
          const status = await getJobStatus(jobId);
          if (cancelled) return;
          setState((s) => ({
            ...s,
            pct: status.pct,
            status: "streaming",
          }));
          if (status.status === "completed") {
            const result = await getJobResult(jobId);
            if (cancelled) return;
            setState((s) => ({
              ...s,
              status: "complete",
              pct: 100,
              summary: result.summary,
              reportCsvUrl: result.report_csv_url,
              reportXlsxUrl: result.report_xlsx_url,
            }));
            stopPolling();
          } else if (status.status === "failed" || status.status === "cancelled") {
            setState((s) => ({
              ...s,
              status: "error",
              error: status.message ?? "Processing failed",
            }));
            stopPolling();
          }
        } catch (err) {
          const message = err instanceof Error ? err.message : "Failed to poll status";
          setState((s) => ({ ...s, status: "error", error: message }));
          stopPolling();
        }
      };
      pollRef.current = window.setInterval(tick, 2000);
      tick();
    };

    const stopPolling = () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };

    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl(jobId));
      wsRef.current = ws;
    } catch (err) {
      const message = err instanceof Error ? err.message : "WebSocket unavailable";
      console.warn("WebSocket failed, falling back to polling:", message);
      startPolling();
      return;
    }

    let opened = false;

    ws.onopen = () => {
      opened = true;
      setState((s) => ({ ...s, status: "streaming" }));
    };

    ws.onmessage = (event) => {
      let msg: WSMessage;
      try {
        msg = JSON.parse(event.data) as WSMessage;
      } catch {
        return;
      }
      switch (msg.type) {
        case "progress":
          setState((s) => ({
            ...s,
            pct: msg.pct,
            processed: msg.processed,
            total: msg.total,
            status: "streaming",
          }));
          break;
        case "frame":
          setState((s) => ({
            ...s,
            frameDataUrl: `data:image/jpeg;base64,${msg.data}`,
          }));
          break;
        case "complete":
          setState((s) => ({
            ...s,
            status: "complete",
            pct: 100,
            summary: msg.summary,
            reportCsvUrl: msg.report_csv_url,
            reportXlsxUrl: msg.report_xlsx_url,
          }));
          break;
        case "error":
          setState((s) => ({ ...s, status: "error", error: msg.message }));
          break;
      }
    };

    ws.onerror = () => {
      if (!opened) {
        // Initial handshake failed; switch to polling.
        startPolling();
      }
    };

    ws.onclose = () => {
      if (!opened) {
        startPolling();
      }
    };

    return () => {
      cancelled = true;
      stopPolling();
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      wsRef.current = null;
    };
  }, [jobId]);

  return state;
}
