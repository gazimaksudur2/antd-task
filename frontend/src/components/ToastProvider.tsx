import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";

export type ToastKind = "info" | "success" | "error" | "warn";

interface Toast {
  id: number;
  kind: ToastKind;
  text: string;
}

export interface ToastApi {
  push: (kind: ToastKind, text: string, ttlMs?: number) => number;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used inside <ToastProvider>");
  }
  return ctx;
}

const KIND_STYLES: Record<ToastKind, string> = {
  info: "border-brand-500/50 bg-brand-900/60 text-brand-100",
  success: "border-emerald-500/50 bg-emerald-900/60 text-emerald-100",
  error: "border-rose-500/60 bg-rose-900/70 text-rose-50",
  warn: "border-amber-500/60 bg-amber-900/60 text-amber-100",
};

export function ToastProvider({ children }: PropsWithChildren) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);
  // Use `window.setTimeout` so the handle is a DOM `number`, not NodeJS.Timeout (avoids
  // clashes when @types/node is installed for vite.config.ts).
  const timeoutsRef = useRef<Map<number, ReturnType<typeof window.setTimeout>>>(new Map());

  const dismiss = useCallback((id: number) => {
    const handle = timeoutsRef.current.get(id);
    if (handle !== undefined) {
      window.clearTimeout(handle);
      timeoutsRef.current.delete(id);
    }
    setToasts((prev: Toast[]) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback<ToastApi["push"]>(
    (kind, text, ttlMs = 5000) => {
      idRef.current += 1;
      const id = idRef.current;
      setToasts((prev: Toast[]) => [...prev, { id, kind, text }]);
      if (ttlMs > 0) {
        const handle = window.setTimeout(() => dismiss(id), ttlMs);
        timeoutsRef.current.set(id, handle);
      }
      return id;
    },
    [dismiss],
  );

  useEffect(() => {
    return () => {
      for (const handle of timeoutsRef.current.values()) {
        window.clearTimeout(handle);
      }
      timeoutsRef.current.clear();
    };
  }, []);

  const value = useMemo(() => ({ push, dismiss }), [push, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed bottom-6 right-6 z-50 flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2"
        aria-live="polite"
        aria-relevant="additions text"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={`pointer-events-auto flex items-start gap-3 rounded-lg border px-4 py-3 text-sm shadow-xl backdrop-blur ${KIND_STYLES[t.kind]}`}
          >
            <div className="flex-1 font-medium leading-snug">{t.text}</div>
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              className="shrink-0 text-xs uppercase tracking-wide opacity-70 hover:opacity-100"
              aria-label="Dismiss notification"
            >
              close
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
