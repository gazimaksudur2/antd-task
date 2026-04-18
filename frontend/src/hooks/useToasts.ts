import { useCallback, useRef, useState } from "react";

import type { ToastMessage } from "../types";

export function useToasts() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const idRef = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (kind: ToastMessage["kind"], text: string, ttlMs = 4500) => {
      idRef.current += 1;
      const id = idRef.current;
      setToasts((prev) => [...prev, { id, kind, text }]);
      if (ttlMs > 0) {
        window.setTimeout(() => dismiss(id), ttlMs);
      }
      return id;
    },
    [dismiss],
  );

  return { toasts, push, dismiss };
}
