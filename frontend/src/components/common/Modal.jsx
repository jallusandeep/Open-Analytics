import { useEffect } from "react";
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
  useEffect(() => {
    if (!open) {
      return undefined;
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        onClose?.();
      }
    }

    document.addEventListener("keydown", handleEscape);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  function handleOverlayClick() {
    if (closeOnOverlay) {
      onClose?.();
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-[10000] flex items-center justify-center px-4 py-6">
      <button
        type="button"
        aria-label="Close modal overlay"
        onClick={handleOverlayClick}
        className="absolute inset-0 cursor-default bg-black/70 backdrop-blur-[2px] animate-[oaMenuIn_0.14s_ease-out]"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label={title || "Modal"}
        className={`relative z-[10001] w-full ${width} overflow-visible rounded border border-oa-border bg-black text-oa-text shadow-2xl animate-[oaMenuIn_0.16s_ease-out]`}
      >
        <div className="flex items-start justify-between gap-4 rounded-t border-b border-oa-border bg-oa-panel px-4 py-3">
          <div className="min-w-0">
            {title && (
              <h2 className={`truncate ${oaCardStyles.modalTitle}`}>
                {title}
              </h2>
            )}

            {subtitle && (
              <p className={`mt-0.5 ${oaCardStyles.modalSubtitle}`}>
                {subtitle}
              </p>
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