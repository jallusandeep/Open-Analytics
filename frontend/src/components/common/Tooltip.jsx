import { useState } from "react";

function Tooltip({ text, children, side = "top" }) {
  const [position, setPosition] = useState({
    top: 0,
    left: 0,
    visible: false
  });

  function showTooltip(event) {
    const rect = event.currentTarget.getBoundingClientRect();

    const width = Math.min(120, Math.max(54, text.length * 6 + 16));
    const height = 22;
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
          className="pointer-events-none fixed z-[9999] truncate rounded border border-oa-border bg-[#151518] px-1.5 py-1 text-center text-[10px] leading-none text-oa-text shadow-xl"
          style={{
            top: `${position.top}px`,
            left: `${position.left}px`,
            width: `${position.width}px`
          }}
        >
          {text}
        </span>
      )}
    </>
  );
}

export default Tooltip;