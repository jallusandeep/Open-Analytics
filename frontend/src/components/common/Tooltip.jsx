import { useCallback, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

function Tooltip({ text, children, side = "top", fixedSide = false }) {
  const triggerRef = useRef(null);
  const tooltipRef = useRef(null);
  const tooltipId = useId();

  const [position, setPosition] = useState({
    top: 0,
    left: 0,
    visible: false,
    ready: false
  });

  const getTooltipPosition = useCallback((triggerRect, tooltipRect) => {
    const gap = 6;
    const screenPadding = 6;

    const sidebar = document.querySelector("aside");
    const sidebarEdge = sidebar?.getBoundingClientRect().right || 0;
    const leftBoundary = triggerRect.left >= sidebarEdge ? Math.max(screenPadding, sidebarEdge + screenPadding) : screenPadding;
    const spaces = {
      top: triggerRect.top - screenPadding - gap,
      bottom: window.innerHeight - triggerRect.bottom - screenPadding - gap,
      left: triggerRect.left - leftBoundary - gap,
      right: window.innerWidth - triggerRect.right - screenPadding - gap
    };
    const fits = (direction) => spaces[direction] >= (direction === "left" || direction === "right" ? tooltipRect.width : tooltipRect.height);
    const opposite = { top: "bottom", bottom: "top", left: "right", right: "left" };
    const directions = ["top", side, opposite[side], "bottom", "right", "left"];
    const direction = fixedSide ? side : directions.find(fits) || Object.keys(spaces).reduce((best, next) => spaces[next] > spaces[best] ? next : best, side);
    let top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2;
    let left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2;
    if (direction === "top") top = triggerRect.top - tooltipRect.height - gap;
    if (direction === "bottom") top = triggerRect.bottom + gap;
    if (direction === "left") left = triggerRect.left - tooltipRect.width - gap;
    if (direction === "right") left = triggerRect.right + gap;
    const minimumLeft = tooltipRect.width <= window.innerWidth - leftBoundary - screenPadding ? leftBoundary : screenPadding;
    return {
      top: Math.max(screenPadding, Math.min(top, window.innerHeight - tooltipRect.height - screenPadding)),
      left: Math.max(minimumLeft, Math.min(left, window.innerWidth - tooltipRect.width - screenPadding))
    };
  }, [side, fixedSide]);

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

    function updatePosition() {
      const nextPosition = getTooltipPosition(triggerRef.current.getBoundingClientRect(), tooltipRef.current.getBoundingClientRect());
      setPosition({ ...nextPosition, visible: true, ready: true });
    }
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [position.visible, text, getTooltipPosition]);

  return (
    <>
      <span
        ref={triggerRef}
        className="inline-flex"
        onMouseEnter={showTooltip}
        onMouseLeave={hideTooltip}
        onFocus={showTooltip}
        onBlur={hideTooltip}
        onPointerDown={hideTooltip}
        aria-describedby={position.visible && text ? tooltipId : undefined}
      >
        {children}
      </span>

      {position.visible && text && createPortal(
        <span
          id={tooltipId}
          role="tooltip"
          ref={tooltipRef}
          className="pointer-events-none fixed z-[30000] max-w-[min(280px,calc(100vw-12px))] max-h-[calc(100vh-12px)] overflow-hidden whitespace-normal break-words rounded border border-oa-border bg-[#151518] px-2 py-1.5 text-center text-[10px] leading-snug text-oa-text shadow-xl"
          style={{
            top: `${position.top}px`,
            left: `${position.left}px`,
            opacity: position.ready ? 1 : 0
          }}
        >
          {text}
        </span>, document.body
      )}
    </>
  );
}

export default Tooltip;
