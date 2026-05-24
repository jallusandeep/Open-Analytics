import {
  ArrowDownAZ,
  ArrowUpAZ,
  Check,
  ChevronRight,
  Filter,
  Palette,
  Search,
  X
} from "lucide-react";
import { useMemo, useState } from "react";

function normalizeValue(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }

  return String(value);
}

function checkboxClassName(checked) {
  return checked
    ? "border-white bg-white text-black"
    : "border-oa-border bg-black text-transparent";
}

function FlyoutMenu({ type }) {
  const options =
    type === "text"
      ? ["Equals", "Does Not Equal", "Contains", "Does Not Contain", "Begins With", "Ends With"]
      : ["No Color", "White", "Grey", "Dark Grey", "Black"];

  return (
    <div className="absolute left-full top-0 z-[70] ml-1 hidden w-44 overflow-hidden rounded border border-oa-border bg-black shadow-2xl group-hover:block">
      {options.map((option) => (
        <button
          key={option}
          type="button"
          className="flex h-8 w-full items-center px-3 text-left text-xs normal-case tracking-normal text-oa-muted transition hover:bg-oa-card hover:text-white"
        >
          {option}
        </button>
      ))}
    </div>
  );
}

export default function TableFilterDropdown({
  columnName,
  values = [],
  selectedValues = [],
  pendingValues = [],
  onChange,
  onApply,
  onCancel,
  onSortAsc,
  onSortDesc,
  onClear,
  align = "left"
}) {
  const [searchText, setSearchText] = useState("");

  const normalizedSelectedValues = pendingValues.length
    ? pendingValues
    : selectedValues;

  const filteredValues = useMemo(() => {
    return values.filter((item) =>
      normalizeValue(item.label || item.value)
        .toLowerCase()
        .includes(searchText.toLowerCase())
    );
  }, [values, searchText]);

  const allValues = useMemo(() => {
    return values.map((item) => normalizeValue(item.value));
  }, [values]);

  const isAllSelected =
    allValues.length > 0 &&
    allValues.every((value) => normalizedSelectedValues.includes(value));

  function toggleValue(value) {
    const normalized = normalizeValue(value);

    if (normalizedSelectedValues.includes(normalized)) {
      onChange(normalizedSelectedValues.filter((item) => item !== normalized));
      return;
    }

    onChange([...normalizedSelectedValues, normalized]);
  }

  function toggleAll() {
    if (isAllSelected) {
      onChange([]);
      return;
    }

    onChange(allValues);
  }

  const flyoutDirection =
    align === "right"
      ? "right-full mr-1 left-auto"
      : "left-full ml-1 right-auto";

  return (
    <div className="w-[310px] max-w-[calc(100vw-32px)] overflow-visible rounded border border-oa-border bg-black text-oa-text shadow-2xl animate-[oaMenuIn_0.14s_ease-out]">
      <div className="py-1">
        <button
          type="button"
          onClick={onSortAsc}
          className="flex h-8 w-full items-center gap-2 px-3 text-left text-xs normal-case tracking-normal text-oa-muted transition hover:bg-oa-card hover:text-white"
        >
          <ArrowDownAZ size={13} />
          <span>Sort A to Z</span>
        </button>

        <button
          type="button"
          onClick={onSortDesc}
          className="flex h-8 w-full items-center gap-2 px-3 text-left text-xs normal-case tracking-normal text-oa-muted transition hover:bg-oa-card hover:text-white"
        >
          <ArrowUpAZ size={13} />
          <span>Sort Z to A</span>
        </button>

        <div className="group relative">
          <button
            type="button"
            className="flex h-8 w-full items-center justify-between px-3 text-left text-xs normal-case tracking-normal text-oa-muted transition hover:bg-oa-card hover:text-white"
          >
            <span className="flex items-center gap-2">
              <Palette size={13} />
              Sort by Color
            </span>
            <ChevronRight size={13} />
          </button>

          <div
            className={`absolute top-0 z-[70] hidden w-44 overflow-hidden rounded border border-oa-border bg-black shadow-2xl group-hover:block ${flyoutDirection}`}
          >
            <button className="flex h-8 w-full items-center px-3 text-xs text-oa-muted hover:bg-oa-card hover:text-white">
              No Color
            </button>
            <button className="flex h-8 w-full items-center px-3 text-xs text-oa-muted hover:bg-oa-card hover:text-white">
              White
            </button>
            <button className="flex h-8 w-full items-center px-3 text-xs text-oa-muted hover:bg-oa-card hover:text-white">
              Grey
            </button>
            <button className="flex h-8 w-full items-center px-3 text-xs text-oa-muted hover:bg-oa-card hover:text-white">
              Black
            </button>
          </div>
        </div>

        <div className="group relative">
          <button
            type="button"
            className="flex h-8 w-full items-center justify-between px-3 text-left text-xs normal-case tracking-normal text-oa-muted transition hover:bg-oa-card hover:text-white"
          >
            <span className="flex items-center gap-2">
              <Filter size={13} />
              Text Filters
            </span>
            <ChevronRight size={13} />
          </button>

          <div
            className={`absolute top-0 z-[70] hidden w-48 overflow-hidden rounded border border-oa-border bg-black shadow-2xl group-hover:block ${flyoutDirection}`}
          >
            {[
              "Equals",
              "Does Not Equal",
              "Contains",
              "Does Not Contain",
              "Begins With",
              "Ends With"
            ].map((item) => (
              <button
                key={item}
                type="button"
                className="flex h-8 w-full items-center px-3 text-left text-xs text-oa-muted hover:bg-oa-card hover:text-white"
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        <div className="group relative">
          <button
            type="button"
            className="flex h-8 w-full items-center justify-between px-3 text-left text-xs normal-case tracking-normal text-oa-muted transition hover:bg-oa-card hover:text-white"
          >
            <span className="flex items-center gap-2">
              <Palette size={13} />
              Filter by Color
            </span>
            <ChevronRight size={13} />
          </button>

          <div
            className={`absolute top-0 z-[70] hidden w-44 overflow-hidden rounded border border-oa-border bg-black shadow-2xl group-hover:block ${flyoutDirection}`}
          >
            <button className="flex h-8 w-full items-center px-3 text-xs text-oa-muted hover:bg-oa-card hover:text-white">
              No Color
            </button>
            <button className="flex h-8 w-full items-center px-3 text-xs text-oa-muted hover:bg-oa-card hover:text-white">
              White
            </button>
            <button className="flex h-8 w-full items-center px-3 text-xs text-oa-muted hover:bg-oa-card hover:text-white">
              Grey
            </button>
            <button className="flex h-8 w-full items-center px-3 text-xs text-oa-muted hover:bg-oa-card hover:text-white">
              Black
            </button>
          </div>
        </div>

        <button
          type="button"
          onClick={onClear}
          className="flex h-8 w-full items-center gap-2 px-3 text-left text-xs normal-case tracking-normal text-oa-muted transition hover:bg-oa-card hover:text-white"
        >
          <X size={13} />
          <span className="truncate">Clear Filter from "{columnName}"</span>
        </button>
      </div>

      <div className="border-y border-oa-border p-2">
        <div className="flex h-8 items-center gap-2 rounded border border-oa-border bg-black px-2 focus-within:border-blue-500">
          <Search size={13} className="text-oa-muted" />
          <input
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="Search values"
            className="w-full bg-transparent text-xs normal-case tracking-normal text-oa-text outline-none placeholder:text-oa-muted"
            autoFocus
          />
        </div>
      </div>

      <div className="max-h-56 overflow-y-auto p-1">
        <button
          type="button"
          onClick={toggleAll}
          className="flex h-8 w-full items-center gap-2 rounded-sm px-2 text-left text-xs normal-case tracking-normal text-oa-muted transition hover:bg-oa-card hover:text-white"
        >
          <span
            className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border ${checkboxClassName(
              isAllSelected
            )}`}
          >
            <Check size={11} />
          </span>
          <span className="truncate">(Select All)</span>
        </button>

        {filteredValues.length === 0 ? (
          <div className="px-2 py-3 text-center text-[11px] normal-case tracking-normal text-oa-muted">
            No values
          </div>
        ) : (
          filteredValues.map((item) => {
            const value = normalizeValue(item.value);
            const label = normalizeValue(item.label);
            const selected = normalizedSelectedValues.includes(value);

            return (
              <button
                key={value}
                type="button"
                onClick={() => toggleValue(value)}
                className="flex h-8 w-full items-center justify-between gap-2 rounded-sm px-2 text-left text-xs normal-case tracking-normal text-oa-muted transition hover:bg-oa-card hover:text-white"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span
                    className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border ${checkboxClassName(
                      selected
                    )}`}
                  >
                    <Check size={11} />
                  </span>

                  <span className="truncate">{label}</span>
                </span>

                {item.count !== undefined && (
                  <span className="shrink-0 text-[10px] text-oa-muted">
                    {item.count}
                  </span>
                )}
              </button>
            );
          })
        )}
      </div>

      <div className="flex items-center justify-end gap-2 border-t border-oa-border px-2 py-2">
        <button
          type="button"
          onClick={onCancel}
          className="flex h-7 w-7 items-center justify-center rounded-sm border border-oa-border bg-black text-oa-muted transition hover:bg-oa-card hover:text-white"
          aria-label="Cancel filter"
          title="Cancel"
        >
          <X size={14} />
        </button>

        <button
          type="button"
          onClick={onApply}
          className="flex h-7 w-7 items-center justify-center rounded-sm border border-oa-border bg-white text-black transition hover:bg-zinc-200"
          aria-label="Apply filter"
          title="Apply"
        >
          <Check size={14} />
        </button>
      </div>
    </div>
  );
}
