import { createPortal } from "react-dom";
import { useContext } from "react";
import Spinner from "./Spinner";
import { LoadingScope } from "./LoadingScope";

export default function ScreenLoading({ message = "Loading" }) {
  const scope = useContext(LoadingScope);
  const target = scope?.element;
  if (scope && !target) return null;
  return createPortal(
    <div role="status" aria-live="polite" className={`${target ? "absolute rounded" : "fixed"} inset-0 z-[20000] flex items-center justify-center bg-black/70 px-4`}>
      <div className="flex items-center gap-2 font-mono text-xs text-oa-muted">
        <Spinner size="sm" color="light" />
        <span>{message}</span>
      </div>
    </div>,
    target || document.body
  );
}
