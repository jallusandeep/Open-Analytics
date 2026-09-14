import { createPortal } from "react-dom";
import Spinner from "./Spinner";

export default function ScreenLoading({ message = "Loading" }) {
  return createPortal(
    <div role="status" aria-live="polite" className="fixed inset-0 z-[20000] flex items-center justify-center bg-black/70 px-4">
      <div className="flex items-center gap-2 font-mono text-xs text-oa-muted">
        <Spinner size="sm" color="light" />
        <span>{message}</span>
      </div>
    </div>,
    document.body
  );
}
