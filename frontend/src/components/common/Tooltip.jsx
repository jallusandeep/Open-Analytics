import { useState } from "react";

function Tooltip({ text, children, side = "top" }) {
  const [position, setPosition] = useState({
    top: 0,
    left: 0,
    visible: false
  });

  function showTooltip(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const safeText = String(text || "");

    const width = Math.min(280, Math.max(72, safeText.length * 6 + 18));
    const estimatedCharsPerLine = Math.max(10, Math.floor((width - 18) / 6));
    const estimatedLines = Math.max(
      1,
      Math.ceil(safeText.length / estimatedCharsPerLine)
    );
    const height = Math.min(160, estimatedLines * 14 + 10);
    const gap = 6;

    let top = rect.top - height - gap;
    let left = rect.left + rect.width / 2 - width / 2;

    if (side === "right") {
      top = rect.top + rect.height / 2 - height / 2;
      left = rect.right + gap;
    }

    if (side === "left") {
      top = rect.top + rect.height / 2 - height / 2;
      left = rect.left - width - gap;
    }

    if (side === "bottom") {
      top = rect.bottom + gap;
      left = rect.left + rect.width / 2 - width / 2;
    }

    if (left + width > window.innerWidth - 6) {
      left = window.innerWidth - width - 6;
    }

    if (left < 6) {
      left = 6;
    }

    if (top < 6) {
      top = rect.bottom + gap;
    }

    if (top + height > window.innerHeight - 6) {
      top = window.innerHeight - height - 6;
    }

    setPosition({
      top,
      left,
      visible: true,
      width
    });
  }

  function hideTooltip() {
    setPosition((previous) => ({
      ...previous,
      visible: false
    }));
  }

  return (
    <>
      <span
        className="inline-flex"
        onMouseEnter={showTooltip}
        onMouseLeave={hideTooltip}
        onFocus={showTooltip}
        onBlur={hideTooltip}
      >
        {children}
      </span>

      {position.visible && text && (
        <span
          className="pointer-events-none fixed z-[9999] whitespace-normal break-words rounded border border-oa-border bg-[#151518] px-2 py-1.5 text-center text-[10px] leading-snug text-oa-text shadow-xl"
          style={{
            top: `${position.top}px`,
            left: `${position.left}px`,
            maxWidth: `${position.width}px`,
            width: "max-content"
          }}
        >
          {text}
        </span>
      )}
    </>
  );
}

export default Tooltip;
