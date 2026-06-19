import { useEffect, useRef, useState } from "react";
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
  onClear
}) {
  const buttonRef = useRef(null);
  const dropdownRef = useRef(null);

  const [position, setPosition] = useState({
    top: 0,
    left: 0,
    flyoutAlign: align
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

    const shouldOpenFlyoutsLeft =
      left + FILTER_DROPDOWN_WIDTH + FILTER_DROPDOWN_FLYOUT_WIDTH >
      window.innerWidth - FILTER_DROPDOWN_SCREEN_GAP;

    setPosition({
      top: rect.bottom + FILTER_DROPDOWN_GAP,
      left,
      flyoutAlign: shouldOpenFlyoutsLeft ? "right" : "left"
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
        title={`Filter ${column.label}`}
      >
        <Filter size={10} />

        {active && <span className={oaHeaderFilterStyles.activeDot} />}
      </button>

      {open &&
        createPortal(
          <div
            ref={dropdownRef}
            className={oaHeaderFilterStyles.portal}
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
            />
          </div>,
          document.body
        )}
    </>
  );
}

export default DataTableHeaderFilter;
