import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Filter } from "lucide-react";

import TableFilterDropdown from "./TableFilterDropdown";

const FILTER_DROPDOWN_WIDTH = 270;
const FILTER_DROPDOWN_GAP = 6;
const FILTER_DROPDOWN_SCREEN_GAP = 12;

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
  onClear
}) {
  const buttonRef = useRef(null);
  const dropdownRef = useRef(null);

  const [position, setPosition] = useState({
    top: 0,
    left: 0
  });

  function calculatePosition() {
    if (!buttonRef.current) {
      return;
    }

    const rect = buttonRef.current.getBoundingClientRect();

    let left =
      align === "right" ? rect.right - FILTER_DROPDOWN_WIDTH : rect.left;

    const minLeft = FILTER_DROPDOWN_SCREEN_GAP;
    const maxLeft =
      window.innerWidth - FILTER_DROPDOWN_WIDTH - FILTER_DROPDOWN_SCREEN_GAP;

    if (left < minLeft) {
      left = minLeft;
    }

    if (left > maxLeft) {
      left = Math.max(minLeft, maxLeft);
    }

    setPosition({
      top: rect.bottom + FILTER_DROPDOWN_GAP,
      left
    });
  }

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    calculatePosition();

    function handlePositionRefresh() {
      calculatePosition();
    }

    function handleClickOutside(event) {
      const clickedButton = buttonRef.current?.contains(event.target);
      const clickedDropdown = dropdownRef.current?.contains(event.target);

      if (!clickedButton && !clickedDropdown) {
        onClose?.();
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    window.addEventListener("resize", handlePositionRefresh);
    window.addEventListener("scroll", handlePositionRefresh, true);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("resize", handlePositionRefresh);
      window.removeEventListener("scroll", handlePositionRefresh, true);
    };
  }, [open, align, onClose]);

  const selected = active || open;

  const buttonStateClass = selected
    ? "border-blue-500 bg-sky-950/30 text-sky-300"
    : "border-oa-border bg-black text-oa-muted hover:border-sky-500/40 hover:bg-oa-card hover:text-white";

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        onClick={onOpen}
        className={`absolute right-3 top-1/2 flex h-[22px] w-[22px] -translate-y-1/2 items-center justify-center rounded-sm border outline-none transition ${buttonStateClass}`}
        aria-label={`Filter ${column.label}`}
        title={`Filter ${column.label}`}
      >
        <Filter size={10} />

        {active && (
          <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full border border-black bg-emerald-400" />
        )}
      </button>

      {open &&
        createPortal(
          <div
            ref={dropdownRef}
            className="fixed z-[9999]"
            style={{
              top: `${position.top}px`,
              left: `${position.left}px`,
              width: `${FILTER_DROPDOWN_WIDTH}px`
            }}
          >
            <TableFilterDropdown
              columnName={column.label}
              values={values}
              selectedValues={selectedValues}
              pendingValues={pendingValues}
              align={align}
              onChange={onChange}
              onApply={onApply}
              onCancel={onCancel}
              onSortAsc={onSortAsc}
              onSortDesc={onSortDesc}
              onClear={onClear}
            />
          </div>,
          document.body
        )}
    </>
  );
}

export default DataTableHeaderFilter;