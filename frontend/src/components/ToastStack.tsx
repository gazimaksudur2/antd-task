import type { ToastMessage } from "../types";

interface Props {
  toasts: ToastMessage[];
  onDismiss: (id: number) => void;
}

const VARIANT_CLASS: Record<ToastMessage["kind"], string> = {
  info: "border-brand-500/40 bg-brand-500/10 text-brand-100",
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-100",
  error: "border-rose-500/40 bg-rose-500/10 text-rose-100",
};

export function ToastStack({ toasts, onDismiss }: Props) {
  return (
    <div className="pointer-events-none fixed bottom-6 right-6 z-50 flex w-full max-w-sm flex-col gap-3">
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 shadow-xl backdrop-blur-md ${VARIANT_CLASS[t.kind]}`}
        >
          <div className="flex-1 text-sm font-medium leading-snug">{t.text}</div>
          <button
            type="button"
            onClick={() => onDismiss(t.id)}
            className="text-xs uppercase tracking-wide opacity-70 hover:opacity-100"
            aria-label="Dismiss notification"
          >
            close
          </button>
        </div>
      ))}
    </div>
  );
}
