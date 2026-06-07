import { useLayoutEffect, useRef, useState } from "react";

function Tooltip({ text, children, side = "top" }) {
  const triggerRef = useRef(null);
  const tooltipRef = useRef(null);

  const [position, setPosition] = useState({
    top: 0,
    left: 0,
    visible: false,
    ready: false
  });

  function getTooltipPosition(triggerRect, tooltipRect) {
    const gap = 6;
    const screenPadding = 6;

    let top = triggerRect.top - tooltipRect.height - gap;
    let left = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2;

    if (side === "right") {
      top = triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2;
      left = triggerRect.right + gap;
    }

    if (side === "left") {
      top = triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2;
      left = triggerRect.left - tooltipRect.width - gap;
    }

    if (side === "bottom") {
      top = triggerRect.bottom + gap;
      left = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2;
    }

    if (left + tooltipRect.width > window.innerWidth - screenPadding) {
      left = window.innerWidth - tooltipRect.width - screenPadding;
    }

    if (left < screenPadding) {
      left = screenPadding;
    }

    if (top < screenPadding) {
      top = triggerRect.bottom + gap;
    }

    if (top + tooltipRect.height > window.innerHeight - screenPadding) {
      top = triggerRect.top - tooltipRect.height - gap;
    }

    if (top < screenPadding) {
      top = screenPadding;
    }

    return { top, left };
  }

  function showTooltip() {
    if (!text) return;

    setPosition((previous) => ({
      ...previous,
      visible: true,
      ready: false
    }));
  }

  function hideTooltip() {
    setPosition((previous) => ({
      ...previous,
      visible: false,
      ready: false
    }));
  }

  useLayoutEffect(() => {
    if (!position.visible || !triggerRef.current || !tooltipRef.current) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    const nextPosition = getTooltipPosition(triggerRect, tooltipRect);

    setPosition({
      top: nextPosition.top,
      left: nextPosition.left,
      visible: true,
      ready: true
    });
  }, [position.visible, text, side]);

  return (
    <>
      <span
        ref={triggerRef}
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
          ref={tooltipRef}
          className="pointer-events-none fixed z-[9999] max-w-[280px] whitespace-normal break-words rounded border border-oa-border bg-[#151518] px-2 py-1.5 text-center text-[10px] leading-snug text-oa-text shadow-xl"
          style={{
            top: `${position.top}px`,
            left: `${position.left}px`,
            opacity: position.ready ? 1 : 0
          }}
        >
          {text}
        </span>
      )}
    </>
  );
}

export default Tooltip;