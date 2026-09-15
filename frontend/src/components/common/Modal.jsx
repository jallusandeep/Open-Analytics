import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

import IconButton from "./IconButton";
import { oaCardStyles } from "./uiStyles";

function Modal({
  open = false,
  title = "",
  subtitle = "",
  children,
  onClose,
  width = "max-w-xl",
  closeOnOverlay = true,
  showCloseButton = true,
  footer = null
}) {
  const [retained, setRetained] = useState(open);
  const visible = open || retained;
  useEffect(() => {
    const timer = window.setTimeout(() => setRetained(open), open ? 0 : 160);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!visible) {
      return undefined;
    }

    function handleEscape(event) {
      if (open && event.key === "Escape") {
        onClose?.();
      }
    }

    document.addEventListener("keydown", handleEscape);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = previousOverflow;
    };
  }, [visible, open, onClose]);

  if (!visible) {
    return null;
  }

  function handleOverlayClick() {
    if (closeOnOverlay) {
      onClose?.();
    }
  }

  return createPortal(
    <div data-state={open ? "open" : "closing"} className={`oa-modal-scifi fixed inset-0 z-[10000] flex items-center justify-center px-4 py-6 ${open ? "" : "pointer-events-none"}`}>
      <button
        type="button"
        aria-label="Close modal overlay"
        onClick={handleOverlayClick}
        className="oa-modal-backdrop absolute inset-0 cursor-default bg-black/70 backdrop-blur-[2px]"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label={title || "Modal"}
        className={`oa-modal-panel relative z-[10001] w-full ${width} overflow-visible rounded border border-oa-border bg-black text-oa-text shadow-2xl`}
      >
        <div className="flex min-h-[48px] items-center justify-between gap-4 rounded-t border-b border-oa-border bg-oa-panel px-4 py-2.5">
          <div className="min-w-0">
            {title && (
              <h2 className={`truncate ${oaCardStyles.modalTitle}`}>
                {title}
              </h2>
            )}
          </div>

          {showCloseButton && (
            <IconButton
              icon={X}
              label="Close"
              onClick={onClose}
              variant="danger"
              tooltipSide="left"
            />
          )}
        </div>

        <div className={`overflow-visible px-4 py-4 ${oaCardStyles.modalBody}`}>
          {children}
        </div>

        {footer && (
          <div className="flex items-center justify-end gap-2 rounded-b border-t border-oa-border bg-black px-4 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}

export default Modal;
