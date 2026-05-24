import {
  ArrowDownAZ,
  ArrowUpAZ,
  Check,
  ChevronRight,
  Filter,
  Palette,
  X
} from "lucide-react";
import { useMemo, useState } from "react";

import SearchBox from "../common/SearchBox";

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

function menuButtonClassName(active) {
  return `flex h-8 w-full items-center justify-between px-3 text-left text-xs normal-case tracking-normal transition ${
    active
      ? "bg-oa-card text-white"
      : "text-oa-muted hover:bg-oa-card hover:text-white"
  }`;
}

function flyoutOptionClassName(active) {
  return `flex h-8 w-full items-center justify-between gap-2 px-3 text-left text-xs normal-case tracking-normal transition ${
    active
      ? "bg-sky-950/30 text-white"
      : "text-oa-muted hover:bg-oa-card hover:text-white"
  }`;
}

function SelectedDot() {
  return <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />;
}

function FlyoutSection({
  label,
  icon: Icon,
  options = [],
  selectedValue,
  onSelect,
  flyoutDirection
}) {
  if (!options.length) {
    return null;
  }

  return (
    <div className="group relative">
      <button type="button" className={menuButtonClassName(Boolean(selectedValue))}>
        <span className="flex items-center gap-2">
          <Icon size={13} />
          {label}
          {selectedValue && <SelectedDot />}
        </span>

        <ChevronRight size={13} />
      </button>

      <div
        className={`absolute top-0 z-[70] hidden overflow-hidden rounded border border-oa-border bg-black shadow-2xl group-hover:block ${flyoutDirection} ${
          label === "Text Filters" ? "w-48" : "w-44"
        }`}
      >
        {options.map((option) => {
          const active = selectedValue === option;

          return (
            <button
              key={option}
              type="button"
              onClick={() => onSelect(option)}
              className={flyoutOptionClassName(active)}
            >
              <span className="truncate">{option}</span>
              {active && <SelectedDot />}
            </button>
          );
        })}
      </div>
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
  align = "left",

  /*
    These are intentionally empty by default.

    If a column really supports these options, pass them from the parent:
    sortColorOptions={["No Color", "White", "Grey", "Black"]}
    textFilterOptions={["Equals", "Contains"]}
    filterColorOptions={["No Color", "White"]}
  */
  sortColorOptions = [],
  textFilterOptions = [],
  filterColorOptions = []
}) {
  const [searchText, setSearchText] = useState("");
  const [selectedSortColor, setSelectedSortColor] = useState("");
  const [selectedTextFilter, setSelectedTextFilter] = useState("");
  const [selectedFilterColor, setSelectedFilterColor] = useState("");

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

  const hasSortAsc = typeof onSortAsc === "function";
  const hasSortDesc = typeof onSortDesc === "function";
  const hasClear = typeof onClear === "function";

  const hasAnyTopOption =
    hasSortAsc ||
    hasSortDesc ||
    sortColorOptions.length > 0 ||
    textFilterOptions.length > 0 ||
    filterColorOptions.length > 0 ||
    hasClear;

  const flyoutDirection =
    align === "right"
      ? "right-full mr-1 left-auto"
      : "left-full ml-1 right-auto";

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

  function handleClear() {
    setSelectedSortColor("");
    setSelectedTextFilter("");
    setSelectedFilterColor("");
    setSearchText("");
    onClear?.();
  }

  function handleApply() {
    onApply?.({
      sortColor: selectedSortColor,
      textFilter: selectedTextFilter,
      filterColor: selectedFilterColor
    });
  }

  return (
    <div className="w-[310px] max-w-[calc(100vw-32px)] overflow-visible rounded border border-oa-border bg-black text-oa-text shadow-2xl animate-[oaMenuIn_0.14s_ease-out]">
      {hasAnyTopOption && (
        <div className="py-1">
          {hasSortAsc && (
            <button
              type="button"
              onClick={onSortAsc}
              className="flex h-8 w-full items-center gap-2 px-3 text-left text-xs normal-case tracking-normal text-oa-muted transition hover:bg-oa-card hover:text-white"
            >
              <ArrowDownAZ size={13} />
              <span>Sort A to Z</span>
            </button>
          )}

          {hasSortDesc && (
            <button
              type="button"
              onClick={onSortDesc}
              className="flex h-8 w-full items-center gap-2 px-3 text-left text-xs normal-case tracking-normal text-oa-muted transition hover:bg-oa-card hover:text-white"
            >
              <ArrowUpAZ size={13} />
              <span>Sort Z to A</span>
            </button>
          )}

          <FlyoutSection
            label="Sort by Color"
            icon={Palette}
            options={sortColorOptions}
            selectedValue={selectedSortColor}
            onSelect={setSelectedSortColor}
            flyoutDirection={flyoutDirection}
          />

          <FlyoutSection
            label="Text Filters"
            icon={Filter}
            options={textFilterOptions}
            selectedValue={selectedTextFilter}
            onSelect={setSelectedTextFilter}
            flyoutDirection={flyoutDirection}
          />

          <FlyoutSection
            label="Filter by Color"
            icon={Palette}
            options={filterColorOptions}
            selectedValue={selectedFilterColor}
            onSelect={setSelectedFilterColor}
            flyoutDirection={flyoutDirection}
          />

          {hasClear && (
            <button
              type="button"
              onClick={handleClear}
              className="flex h-8 w-full items-center gap-2 px-3 text-left text-xs normal-case tracking-normal text-red-400 transition hover:bg-red-950/40 hover:text-red-300"
            >
              <X size={13} />
              <span className="truncate">Clear Filter from "{columnName}"</span>
            </button>
          )}
        </div>
      )}

      <div className="border-y border-oa-border p-2">
        <SearchBox
          value={searchText}
          onChange={setSearchText}
          onClear={() => setSearchText("")}
          placeholder="Search values"
          className="w-full"
          inputClassName="normal-case tracking-normal text-oa-text"
          iconSize={13}
        />
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
                className={`flex h-8 w-full items-center justify-between gap-2 rounded-sm px-2 text-left text-xs normal-case tracking-normal transition ${
                  selected
                    ? "bg-oa-card/70 text-white"
                    : "text-oa-muted hover:bg-oa-card hover:text-white"
                }`}
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
          className="flex h-7 w-7 items-center justify-center rounded-sm border border-oa-border bg-black text-red-400 transition hover:border-red-500/60 hover:bg-red-950/40 hover:text-red-300"
          aria-label="Cancel filter"
          title="Cancel"
        >
          <X size={14} />
        </button>

        <button
          type="button"
          onClick={handleApply}
          className="flex h-7 w-7 items-center justify-center rounded-sm border border-oa-border bg-black text-emerald-300 transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500"
          aria-label="Apply filter"
          title="Apply"
        >
          <Check size={14} />
        </button>
      </div>
    </div>
  );
}
