import { CalendarDays, ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { oaIconButtonStyles, oaInputStyles } from "./uiStyles";

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
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
  min,
  max,
  disabled = false
}) {
  const selectedDate = parseDate(value);
  const today = new Date();
  const inputRef = useRef(null);
  const calendarButtonRef = useRef(null);
  const popoverRef = useRef(null);

  const [open, setOpen] = useState(false);
  const [pickerView, setPickerView] = useState("day");
  const [calendarTransition, setCalendarTransition] = useState("zoom-in");
  const [yearPageStart, setYearPageStart] = useState(Math.floor((selectedDate || today).getFullYear() / 12) * 12);
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
    setCalendarTransition(offset > 0 ? "slide-left" : "slide-right");
    if (pickerView === "year") {
      setYearPageStart((current) => current + offset * 12);
    } else if (pickerView === "month") {
      setViewDate(new Date(viewDate.getFullYear() + offset, viewDate.getMonth(), 1));
    } else {
      setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + offset, 1));
    }
  }

  function monthInRange(year, month) {
    const first = toDateValue(new Date(year, month, 1));
    const last = toDateValue(new Date(year, month + 1, 0));
    return (!min || last >= min) && (!max || first <= max);
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
    if ((min && nextValue < min) || (max && nextValue > max)) return;
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
    setYearPageStart(Math.floor((selectedDate || today).getFullYear() / 12) * 12);
    setPickerView("day");
    setCalendarTransition("zoom-in");
    setOpen(true);
  }

  function handleInputChange(event) {
    const nextValue = event.target.value;
    setDraftValue(nextValue);

    const normalizedValue = normalizeTypedDate(nextValue);
    if (parseDate(normalizedValue) && ((min && normalizedValue < min) || (max && normalizedValue > max))) return;
    emitChange(normalizedValue);

    const parsed = parseDate(normalizedValue);
    if (parsed) {
      setViewDate(parsed);
    }
  }

  function handleInputBlur() {
    const normalizedValue = normalizeTypedDate(draftValue);

    if (parseDate(normalizedValue) && ((min && normalizedValue < min) || (max && normalizedValue > max))) {
      setDraftValue(value || "");
      return;
    }

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

  function selectDateSegment(event) {
    const input = event.currentTarget;
    const cursor = input.selectionStart ?? 0;
    const [start, end] = cursor <= 4 ? [0, 4] : cursor <= 7 ? [5, 7] : [8, 10];
    input.setSelectionRange(start, end);
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

    document.addEventListener("pointerdown", handlePointerDown, true);
    document.addEventListener("keydown", handleKeyDown);
    window.addEventListener("resize", handleViewportChange);
    window.addEventListener("scroll", handleViewportChange, true);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown, true);
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
        onClick={selectDateSegment}
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
        className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-sky-300 transition hover:bg-oa-card hover:text-sky-200 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={`${ariaLabel} calendar`}
        aria-expanded={open}
      >
        <CalendarDays size={14} />
      </button>

      {draftValue && !disabled ? (
        <button
          type="button"
          onClick={clearDate}
          className="absolute right-7 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-oa-muted transition hover:bg-oa-card hover:text-white"
          aria-label={`Clear ${ariaLabel}`}
        >
          <X size={12} />
        </button>
      ) : null}

      {open ? createPortal(
        <div
          ref={popoverRef}
          className="fixed z-[20000] w-[280px] rounded border border-oa-border bg-black p-2 font-mono shadow-2xl animate-[oaMenuIn_0.14s_ease-out]"
          style={{
            top: `${popoverPosition.top}px`,
            left: `${popoverPosition.left}px`
          }}
        >
          <div>
            <div className="mb-2 flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => changeMonth(-1)}
                className="flex h-7 w-7 items-center justify-center rounded border border-oa-border bg-black text-oa-muted transition hover:border-sky-500/50 hover:bg-oa-card hover:text-sky-200"
                aria-label="Previous month"
              >
                <ChevronLeft size={14} />
              </button>

              <button type="button" onClick={() => {
                setYearPageStart(Math.floor(viewDate.getFullYear() / 12) * 12);
                setCalendarTransition("zoom-out");
                setPickerView("year");
              }} className="min-w-0 flex-1 rounded py-1 text-center text-[12px] font-semibold tracking-[-0.01em] text-white hover:bg-oa-card hover:text-sky-200 focus-visible:outline focus-visible:outline-sky-400" aria-label="Choose year and month">
                {pickerView === "year" ? `${yearPageStart} – ${yearPageStart + 11}` : pickerView === "month" ? viewDate.getFullYear() : viewDate.toLocaleDateString("en-IN", {
                  month: "long",
                  year: "numeric"
                })}
              </button>

              <button
                type="button"
                onClick={() => changeMonth(1)}
                className="flex h-7 w-7 items-center justify-center rounded border border-oa-border bg-black text-oa-muted transition hover:border-sky-500/50 hover:bg-oa-card hover:text-sky-200"
                aria-label="Next month"
              >
                <ChevronRight size={14} />
              </button>
            </div>

            <div key={`${pickerView}-${pickerView === "year" ? yearPageStart : viewDate.getFullYear()}-${pickerView === "day" ? viewDate.getMonth() : ""}`} className={`min-h-[252px] motion-reduce:animate-none ${calendarTransition === "slide-left" ? "animate-[oaCalendarSlideLeft_0.18s_ease-out]" : calendarTransition === "slide-right" ? "animate-[oaCalendarSlideRight_0.18s_ease-out]" : calendarTransition === "zoom-out" ? "animate-[oaCalendarZoomOut_0.18s_ease-out]" : "animate-[oaCalendarZoom_0.18s_ease-out]"}`}>
            {pickerView === "year" ? (
              <div className="grid grid-cols-3 gap-2 p-1">
                {Array.from({ length: 12 }, (_, index) => yearPageStart + index).map((year) => {
                  const available = Array.from({ length: 12 }, (_, month) => monthInRange(year, month)).some(Boolean);
                  return <button key={year} type="button" disabled={!available} onClick={() => {
                    setViewDate(new Date(year, viewDate.getMonth(), 1));
                    setCalendarTransition("zoom-in");
                    setPickerView("month");
                  }} className={`h-12 rounded border text-xs transition hover:border-sky-500/50 hover:bg-oa-card disabled:cursor-not-allowed disabled:opacity-25 ${year === viewDate.getFullYear() ? "border-sky-500/60 bg-sky-950/30 text-white" : "border-oa-border text-oa-muted"}`}>{year}</button>;
                })}
              </div>
            ) : pickerView === "month" ? (
              <div className="grid grid-cols-3 gap-2 p-1">
                {MONTHS.map((month, index) => <button key={month} type="button" disabled={!monthInRange(viewDate.getFullYear(), index)} onClick={() => {
                  setViewDate(new Date(viewDate.getFullYear(), index, 1));
                  setCalendarTransition("zoom-in");
                  setPickerView("day");
                }} className={`h-12 rounded border text-xs transition hover:border-sky-500/50 hover:bg-oa-card disabled:cursor-not-allowed disabled:opacity-25 ${index === viewDate.getMonth() ? "border-sky-500/60 bg-sky-950/30 text-white" : "border-oa-border text-oa-muted"}`}>{month}</button>)}
              </div>
            ) : <div className="grid grid-cols-7 gap-1 rounded bg-black p-1">
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
                const outOfRange = Boolean((min && dateValue < min) || (max && dateValue > max));

                return (
                  <button
                    key={dateValue}
                    type="button"
                    onClick={() => selectDate(date)}
                    disabled={outOfRange}
                    className={`flex h-8 items-center justify-center rounded border text-[11px] tracking-[-0.01em] outline-none transition ${
                      selected
                        ? "border-sky-400 bg-sky-500 text-black"
                        : currentDay
                          ? "border-emerald-500/50 bg-emerald-950/30 text-emerald-200"
                          : "border-transparent bg-transparent text-oa-muted hover:border-sky-500/30 hover:bg-oa-card hover:text-white"
                    } ${inMonth ? "" : "opacity-35"} disabled:cursor-not-allowed disabled:opacity-20`}
                    aria-label={`Select ${formatDateLabel(dateValue)}`}
                  >
                    {date.getDate()}
                  </button>
                );
              })}
            </div>}
            </div>

            <div className="mt-2 flex items-center justify-between border-t border-oa-border pt-2">
              <button
                type="button"
                onClick={() => selectDate(today)}
                disabled={Boolean((min && toDateValue(today) < min) || (max && toDateValue(today) > max))}
                className="h-7 rounded border border-oa-border bg-black px-2 text-[11px] tracking-[-0.01em] text-emerald-200 transition hover:border-emerald-500/50 hover:bg-emerald-950/30 disabled:cursor-not-allowed disabled:opacity-40"
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
        </div>, document.body
      ) : null}
    </div>
  );
}

export default DatePicker;
