import { CalendarDays, ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { oaIconButtonStyles, oaInputStyles } from "./uiStyles";

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
const POPOVER_WIDTH = 280;
const POPOVER_HEIGHT = 342;
const SAFE_PADDING = 8;
const GAP = 6;

function parseDate(value) {
  if (!value) {
    return null;
  }

  const [year, month, day] = String(value).split("-").map(Number);

  if (!year || !month || !day) {
    return null;
  }

  const parsed = new Date(year, month - 1, day);

  if (
    Number.isNaN(parsed.getTime()) ||
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month - 1 ||
    parsed.getDate() !== day
  ) {
    return null;
  }

  return parsed;
}

function toDateValue(date) {
  return [
    String(date.getFullYear()),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0")
  ].join("-");
}

function formatDateLabel(value) {
  const parsed = parseDate(value);

  if (!parsed) {
    return "";
  }

  return parsed.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  });
}

function sameDay(left, right) {
  if (!left || !right) {
    return false;
  }

  return toDateValue(left) === toDateValue(right);
}

function normalizeTypedDate(value) {
  const cleanValue = String(value || "").trim();

  if (!cleanValue) {
    return "";
  }

  const match = cleanValue.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);

  if (!match) {
    return cleanValue;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const parsed = new Date(year, month - 1, day);

  if (
    Number.isNaN(parsed.getTime()) ||
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month - 1 ||
    parsed.getDate() !== day
  ) {
    return cleanValue;
  }

  return toDateValue(parsed);
}

function DatePicker({
  name,
  value = "",
  onChange,
  placeholder = "YYYY-MM-DD",
  className = "",
  ariaLabel = "Select date",
  disabled = false
}) {
  const selectedDate = parseDate(value);
  const today = new Date();
  const inputRef = useRef(null);
  const calendarButtonRef = useRef(null);
  const popoverRef = useRef(null);

  const [open, setOpen] = useState(false);
  const [draftValue, setDraftValue] = useState(value || "");
  const [viewDate, setViewDate] = useState(selectedDate || today);
  const [popoverPosition, setPopoverPosition] = useState({
    top: 0,
    left: 0
  });

  const calendarDays = useMemo(() => {
    const year = viewDate.getFullYear();
    const month = viewDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const startDate = new Date(year, month, 1 - firstDay.getDay());

    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(startDate);
      date.setDate(startDate.getDate() + index);

      return {
        date,
        value: toDateValue(date),
        inMonth: date.getMonth() === month
      };
    });
  }, [viewDate]);

  useEffect(() => {
    setDraftValue(value || "");

    const parsed = parseDate(value);
    if (parsed) {
      setViewDate(parsed);
    }
  }, [value]);

  function emitChange(nextValue) {
    onChange?.({
      target: {
        name,
        value: nextValue
      }
    });
  }

  function changeMonth(offset) {
    setViewDate(
      new Date(viewDate.getFullYear(), viewDate.getMonth() + offset, 1)
    );
  }

  function placePopover() {
    const anchor = inputRef.current || calendarButtonRef.current;

    if (!anchor) {
      return;
    }

    const rect = anchor.getBoundingClientRect();
    const viewportWidth =
      window.innerWidth || document.documentElement.clientWidth;
    const viewportHeight =
      window.innerHeight || document.documentElement.clientHeight;

    const spaceBelow = viewportHeight - rect.bottom - SAFE_PADDING;
    const spaceAbove = rect.top - SAFE_PADDING;
    const opensUp = spaceBelow < POPOVER_HEIGHT && spaceAbove > spaceBelow;

    const top = opensUp
      ? Math.max(SAFE_PADDING, rect.top - POPOVER_HEIGHT - GAP)
      : Math.min(
          rect.bottom + GAP,
          Math.max(SAFE_PADDING, viewportHeight - POPOVER_HEIGHT - SAFE_PADDING)
        );

    const left = Math.min(
      Math.max(SAFE_PADDING, rect.left),
      Math.max(SAFE_PADDING, viewportWidth - POPOVER_WIDTH - SAFE_PADDING)
    );

    setPopoverPosition({ top, left });
  }

  function selectDate(date) {
    const nextValue = toDateValue(date);
    setDraftValue(nextValue);
    emitChange(nextValue);
    setOpen(false);
  }

  function clearDate(event) {
    event.stopPropagation();
    setDraftValue("");
    emitChange("");
    setOpen(false);
    inputRef.current?.focus();
  }

  function openCalendar() {
    if (disabled) {
      return;
    }

    setViewDate(selectedDate || today);
    setOpen(true);
  }

  function handleInputChange(event) {
    const nextValue = event.target.value;
    setDraftValue(nextValue);

    const normalizedValue = normalizeTypedDate(nextValue);
    emitChange(normalizedValue);

    const parsed = parseDate(normalizedValue);
    if (parsed) {
      setViewDate(parsed);
    }
  }

  function handleInputBlur() {
    const normalizedValue = normalizeTypedDate(draftValue);

    if (normalizedValue !== draftValue) {
      setDraftValue(normalizedValue);
      emitChange(normalizedValue);
    }
  }

  function handleInputKeyDown(event) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      openCalendar();
    }

    if (event.key === "Escape") {
      setOpen(false);
    }
  }

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    window.requestAnimationFrame(placePopover);

    function handlePointerDown(event) {
      if (
        inputRef.current?.contains(event.target) ||
        calendarButtonRef.current?.contains(event.target) ||
        popoverRef.current?.contains(event.target)
      ) {
        return;
      }

      setOpen(false);
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    function handleViewportChange() {
      placePopover();
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    window.addEventListener("resize", handleViewportChange);
    window.addEventListener("scroll", handleViewportChange, true);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("resize", handleViewportChange);
      window.removeEventListener("scroll", handleViewportChange, true);
    };
  }, [open, selectedDate]);

  return (
    <div className={`relative h-8 ${className}`}>
      <input
        ref={inputRef}
        name={name}
        type="text"
        inputMode="numeric"
        value={draftValue}
        disabled={disabled}
        onFocus={placePopover}
        onChange={handleInputChange}
        onBlur={handleInputBlur}
        onKeyDown={handleInputKeyDown}
        placeholder={placeholder}
        className={`${oaInputStyles.base} h-8 w-full pr-14 oa-code-font text-[12px] hover:border-sky-500/40 hover:bg-oa-card ${
          open ? "border-blue-500 bg-oa-card" : ""
        } ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
        aria-label={ariaLabel}
      />

      <button
        ref={calendarButtonRef}
        type="button"
        onClick={() => {
          if (open) {
            setOpen(false);
            return;
          }

          openCalendar();
        }}
        disabled={disabled}
        className="absolute right-7 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-sky-300 transition hover:bg-oa-card hover:text-sky-200 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={`${ariaLabel} calendar`}
        aria-expanded={open}
      >
        <CalendarDays size={14} />
      </button>

      {draftValue && !disabled ? (
        <button
          type="button"
          onClick={clearDate}
          className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-oa-muted transition hover:bg-oa-card hover:text-white"
          aria-label={`Clear ${ariaLabel}`}
        >
          <X size={12} />
        </button>
      ) : null}

      {open ? (
        <div
          ref={popoverRef}
          className="fixed z-[9999] w-[280px] rounded border border-oa-border bg-black p-2 font-mono shadow-2xl animate-[oaMenuIn_0.14s_ease-out]"
          style={{
            top: `${popoverPosition.top}px`,
            left: `${popoverPosition.left}px`
          }}
        >
          <div className="rounded border border-oa-border bg-[#070708] p-2">
            <div className="mb-2 flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => changeMonth(-1)}
                className="flex h-7 w-7 items-center justify-center rounded border border-oa-border bg-black text-oa-muted transition hover:border-sky-500/50 hover:bg-oa-card hover:text-sky-200"
                aria-label="Previous month"
              >
                <ChevronLeft size={14} />
              </button>

              <span className="min-w-0 flex-1 text-center text-[12px] font-semibold tracking-[-0.01em] text-white">
                {viewDate.toLocaleDateString("en-IN", {
                  month: "long",
                  year: "numeric"
                })}
              </span>

              <button
                type="button"
                onClick={() => changeMonth(1)}
                className="flex h-7 w-7 items-center justify-center rounded border border-oa-border bg-black text-oa-muted transition hover:border-sky-500/50 hover:bg-oa-card hover:text-sky-200"
                aria-label="Next month"
              >
                <ChevronRight size={14} />
              </button>
            </div>

            <div className="grid grid-cols-7 gap-1 rounded bg-black p-1">
              {WEEKDAYS.map((weekday) => (
                <div
                  key={weekday}
                  className="flex h-6 items-center justify-center text-[10px] font-semibold tracking-[-0.01em] text-oa-muted"
                >
                  {weekday}
                </div>
              ))}

              {calendarDays.map(({ date, value: dateValue, inMonth }) => {
                const selected = sameDay(date, selectedDate);
                const currentDay = sameDay(date, today);

                return (
                  <button
                    key={dateValue}
                    type="button"
                    onClick={() => selectDate(date)}
                    className={`flex h-8 items-center justify-center rounded border text-[11px] tracking-[-0.01em] outline-none transition ${
                      selected
                        ? "border-sky-400 bg-sky-500 text-black"
                        : currentDay
                          ? "border-emerald-500/50 bg-emerald-950/30 text-emerald-200"
                          : "border-transparent bg-transparent text-oa-muted hover:border-sky-500/30 hover:bg-oa-card hover:text-white"
                    } ${inMonth ? "" : "opacity-35"}`}
                    aria-label={`Select ${formatDateLabel(dateValue)}`}
                  >
                    {date.getDate()}
                  </button>
                );
              })}
            </div>

            <div className="mt-2 flex items-center justify-between border-t border-oa-border pt-2">
              <button
                type="button"
                onClick={() => selectDate(today)}
                className="h-7 rounded border border-oa-border bg-black px-2 text-[11px] tracking-[-0.01em] text-emerald-200 transition hover:border-emerald-500/50 hover:bg-emerald-950/30"
              >
                Today
              </button>

              <button
                type="button"
                onClick={() => setOpen(false)}
                className={`${oaIconButtonStyles.base} ${oaIconButtonStyles.variantButton.default} ${oaIconButtonStyles.variantIcon.default} h-7 w-7`}
                aria-label="Close date picker"
              >
                <X size={13} />
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default DatePicker;