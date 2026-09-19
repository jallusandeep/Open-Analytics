import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Filter } from "lucide-react";

import { oaHeaderFilterStyles } from "../common/uiStyles";
import TableFilterDropdown from "./TableFilterDropdown";

const FILTER_DROPDOWN_WIDTH = 310;
const FILTER_DROPDOWN_GAP = 6;
const FILTER_DROPDOWN_SCREEN_GAP = 12;
const FILTER_DROPDOWN_FLYOUT_WIDTH = 200;

function DataTableHeaderFilter({
  column,
  active = false,
  open = false,
  align = "left",
  values = [],
  selectedValues = [],
  pendingValues = [],
  onOpen,
  onClose,
  onChange,
  onApply,
  onCancel,
  onSortAsc,
  onSortDesc,
  onClear,
  conditionalFormatting,
  onToggleConditionalFormatting
}) {
  const buttonRef = useRef(null);
  const dropdownRef = useRef(null);
  const [mounted, setMounted] = useState(open);

  const [position, setPosition] = useState({
    top: 0,
    left: 0,
    flyoutAlign: align,
    direction: "down"
  });

  useEffect(() => {
    if (open) {
      const timer = window.setTimeout(() => setMounted(true), 0);
      return () => window.clearTimeout(timer);
    }
    const timer = window.setTimeout(() => setMounted(false), 120);
    return () => window.clearTimeout(timer);
  }, [open]);

  function calculatePosition() {
    if (!buttonRef.current) {
      return;
    }

    const rect = buttonRef.current.getBoundingClientRect();

    const minLeft = FILTER_DROPDOWN_SCREEN_GAP;
    const menuWidth = Math.min(FILTER_DROPDOWN_WIDTH, window.innerWidth - minLeft * 2);
    const roomRight = window.innerWidth - rect.left - minLeft;
    const roomLeft = rect.right - minLeft;
    const openLeft = roomRight < menuWidth && roomLeft > roomRight;
    const left = Math.max(minLeft, Math.min(openLeft ? rect.right - menuWidth : rect.left, window.innerWidth - menuWidth - minLeft));
    const menuHeight = dropdownRef.current?.getBoundingClientRect().height || 420;
    const roomBelow = window.innerHeight - rect.bottom - FILTER_DROPDOWN_GAP - minLeft;
    const roomAbove = rect.top - FILTER_DROPDOWN_GAP - minLeft;
    const direction = roomBelow < menuHeight && roomAbove > roomBelow ? "up" : "down";
    const top = direction === "up"
      ? Math.max(minLeft, rect.top - menuHeight - FILTER_DROPDOWN_GAP)
      : Math.max(minLeft, Math.min(rect.bottom + FILTER_DROPDOWN_GAP, window.innerHeight - menuHeight - minLeft));
    const flyoutRoomRight = window.innerWidth - (left + menuWidth) - minLeft;
    const flyoutRoomLeft = left - minLeft;
    const flyoutAlign = flyoutRoomRight >= FILTER_DROPDOWN_FLYOUT_WIDTH || flyoutRoomRight >= flyoutRoomLeft
      ? "left" : "right";

    setPosition((previous) =>
      previous.top === top && previous.left === left &&
      previous.flyoutAlign === flyoutAlign && previous.direction === direction
        ? previous : { top, left, flyoutAlign, direction }
    );
  }

  useLayoutEffect(() => {
    if (open) calculatePosition();
  }, [open, align]);

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    let frame = null;
    function handlePositionRefresh(event) {
      // Scrolling values inside the portal does not move its anchor.
      if (event.target instanceof Node && dropdownRef.current?.contains(event.target)) return;
      if (frame !== null) return;
      frame = window.requestAnimationFrame(() => {
        frame = null;
        calculatePosition();
      });
    }

    function handleClickOutside(event) {
      const clickedButton = buttonRef.current?.contains(event.target);
      const clickedDropdown = dropdownRef.current?.contains(event.target);

      if (!clickedButton && !clickedDropdown) {
        onClose?.();
      }
    }

    document.addEventListener("pointerdown", handleClickOutside, true);
    window.addEventListener("resize", handlePositionRefresh);
    window.addEventListener("scroll", handlePositionRefresh, true);

    return () => {
      if (frame !== null) window.cancelAnimationFrame(frame);
      document.removeEventListener("pointerdown", handleClickOutside, true);
      window.removeEventListener("resize", handlePositionRefresh);
      window.removeEventListener("scroll", handlePositionRefresh, true);
    };
  }, [open, align, onClose]);

  const selected = active || open;

  const buttonStateClass = selected
    ? oaHeaderFilterStyles.buttonSelected
    : oaHeaderFilterStyles.buttonDefault;

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        onClick={onOpen}
        className={`${oaHeaderFilterStyles.button} ${buttonStateClass}`}
        aria-label={`Filter ${column.label}`}

      >
        <Filter size={10} />

        {active && <span className={oaHeaderFilterStyles.activeDot} />}
      </button>

      {mounted &&
        createPortal(
          <div
            ref={dropdownRef}
            data-state={open ? "open" : "closing"}
            className={`${oaHeaderFilterStyles.portal} ${position.direction === "up" ? (open ? "origin-bottom animate-[oaMenuIn_0.1s_ease-out]" : "origin-bottom animate-[oaMenuOut_0.12s_ease-in]") : (open ? "origin-top animate-[oaSelectDown_0.1s_ease-out]" : "origin-top animate-[oaSelectUp_0.12s_ease-in]")}`}
            style={{
              top: `${position.top}px`,
              left: `${position.left}px`,
              width: `${FILTER_DROPDOWN_WIDTH}px`,
              maxWidth: `calc(100vw - ${FILTER_DROPDOWN_SCREEN_GAP * 2}px)`
            }}
          >
            <TableFilterDropdown
              columnName={column.label}
              values={values}
              selectedValues={selectedValues}
              pendingValues={pendingValues}
              align={position.flyoutAlign}
              onChange={onChange}
              onApply={onApply}
              onCancel={onCancel}
              onSortAsc={onSortAsc}
              onSortDesc={onSortDesc}
              onClear={onClear}
              conditionalFormatting={conditionalFormatting}
              onToggleConditionalFormatting={onToggleConditionalFormatting}
            />
          </div>,
          document.body
        )}
    </>
  );
}

export default DataTableHeaderFilter;
