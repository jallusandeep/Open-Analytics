import {
  ArrowDownAZ,
  ArrowUpAZ,
  Check,
  ChevronRight,
  Filter,
  Palette,
  X
} from "lucide-react";
import { useLayoutEffect, useMemo, useRef, useState } from "react";

import SearchBox from "../common/SearchBox";
import { oaTableFilterDropdownStyles } from "../common/uiStyles";

function normalizeValue(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }

  return String(value);
}

function optionValue(item) {
  return normalizeValue(typeof item === "object" && item !== null ? item.value : item);
}

function optionLabel(item) {
  if (typeof item !== "object" || item === null) return normalizeValue(item);
  return normalizeValue(item.label ?? item.value);
}

// Fixed-height options keep opening and scrolling independent of value count.
function FilterValueList({ values, selectedValueSet, toggleValue, toggleAll, isAllSelected }) {
  const listRef = useRef(null);
  const focusIndexRef = useRef(null);
  const [scrollTop, setScrollTop] = useState(0);
  const rowHeight = 32;
  const overscan = 5;
  const start = Math.max(0, Math.floor(Math.max(0, scrollTop - rowHeight) / rowHeight) - overscan);
  const end = Math.min(values.length, start + 18);

  useLayoutEffect(() => {
    if (focusIndexRef.current === null) return;
    const button = listRef.current?.querySelector(`[data-value-index="${focusIndexRef.current}"]`);
    if (button) {
      button.focus({ preventScroll: true });
      focusIndexRef.current = null;
    }
  });

  function navigate(event) {
    const index = Number(event.target.dataset.valueIndex);
    if (!Number.isInteger(index)) return;
    let next;
    if (event.key === "ArrowDown" || (event.key === "Tab" && !event.shiftKey)) next = index + 1;
    else if (event.key === "ArrowUp" || (event.key === "Tab" && event.shiftKey)) next = index - 1;
    else if (event.key === "Home") next = -1;
    else if (event.key === "End") next = values.length - 1;
    else return;
    if (next < -1 || next >= values.length) return;
    event.preventDefault();
    const top = (next + 1) * rowHeight;
    const list = listRef.current;
    if (top < list.scrollTop) list.scrollTop = top;
    else if (top + rowHeight > list.scrollTop + list.clientHeight - 8) {
      list.scrollTop = top + rowHeight - list.clientHeight + 8;
    }
    const button = list.querySelector(`[data-value-index="${next}"]`);
    if (button) button.focus({ preventScroll: true });
    else focusIndexRef.current = next;
    setScrollTop(list.scrollTop);
  }

  function checkbox(checked) {
    return <span className={`${oaTableFilterDropdownStyles.checkbox} ${checked
      ? oaTableFilterDropdownStyles.checkboxChecked : oaTableFilterDropdownStyles.checkboxUnchecked}`}>
      <Check size={11} />
    </span>;
  }

  return <div ref={listRef} className={oaTableFilterDropdownStyles.valuesSection}
    onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)} onKeyDown={navigate}>
    <button type="button" data-value-index={-1} onClick={toggleAll}
      aria-pressed={isAllSelected} className={oaTableFilterDropdownStyles.valueButton}>
      {checkbox(isAllSelected)}<span className="truncate">(Select All)</span>
    </button>
    {values.length === 0 ? <div className={oaTableFilterDropdownStyles.emptyValues}>No values</div> : <>
      <div aria-hidden="true" style={{ height: start * rowHeight }} />
      {values.slice(start, end).map((item, offset) => {
        const value = optionValue(item);
        const selected = selectedValueSet.has(value);
        return <button key={value} type="button" data-value-index={start + offset}
          aria-pressed={selected} onClick={() => toggleValue(value)}
          className={`${oaTableFilterDropdownStyles.valueRow} ${selected
            ? oaTableFilterDropdownStyles.valueRowSelected : oaTableFilterDropdownStyles.valueRowDefault}`}>
          <span className={oaTableFilterDropdownStyles.valueLeft}>
            {checkbox(selected)}<span className="truncate">{optionLabel(item)}</span>
          </span>
          {item?.count !== undefined && <span className={oaTableFilterDropdownStyles.valueCount}>{item.count}</span>}
        </button>;
      })}
      <div aria-hidden="true" style={{ height: (values.length - end) * rowHeight }} />
    </>}
  </div>;
}

function SelectedDot() {
  return <span className={oaTableFilterDropdownStyles.selectedDot} />;
}

function FlyoutSection({
  label,
  icon: Icon,
  options = [],
  selectedValue,
  onSelect,
  flyoutDirection
}) {
  const [flyoutOpen, setFlyoutOpen] = useState(false);
  if (!options.length) {
    return null;
  }

  return (
    <div className={oaTableFilterDropdownStyles.flyoutWrapper}>
      <div
        role="button"
        tabIndex={0}
        aria-expanded={flyoutOpen}
        onClick={() => {
          if (window.getSelection()?.isCollapsed !== false) setFlyoutOpen((current) => !current);
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            setFlyoutOpen((current) => !current);
          }
        }}
        className={`${oaTableFilterDropdownStyles.menuButton} ${
          selectedValue
            ? oaTableFilterDropdownStyles.menuButtonActive
            : oaTableFilterDropdownStyles.menuButtonDefault
        }`}
      >
        <span className={`${oaTableFilterDropdownStyles.menuButtonLeft} select-text`}>
          <Icon size={13} />
          {label}
          {selectedValue && <SelectedDot />}
        </span>

        <ChevronRight size={13} />
      </div>

      {flyoutOpen ? <div
        onClick={(event) => event.stopPropagation()}
        className={`${oaTableFilterDropdownStyles.flyoutMenu} ${flyoutDirection} ${
          label === "Text Filters"
            ? oaTableFilterDropdownStyles.flyoutWide
            : oaTableFilterDropdownStyles.flyoutNormal
        }`}
      >
        {options.map((option) => {
          const active = selectedValue === option;

          return (
            <button
              key={option}
              type="button"
              onClick={() => { onSelect(option); setFlyoutOpen(false); }}
              className={`${oaTableFilterDropdownStyles.flyoutOption} ${
                active
                  ? oaTableFilterDropdownStyles.flyoutOptionActive
                  : oaTableFilterDropdownStyles.flyoutOptionDefault
              }`}
            >
              <span className="truncate">{option}</span>
              {active && <SelectedDot />}
            </button>
          );
        })}
      </div> : null}
    </div>
  );
}

export default function TableFilterDropdown({
  columnName,
  values = [],
  selectedValues = [],
  pendingValues,
  onChange,
  onApply,
  onCancel,
  onSortAsc,
  conditionalFormatting = false,
  onToggleConditionalFormatting,
  onSortDesc,
  onClear,
  align = "left",

  sortColorOptions = [],
  textFilterOptions = [],
  filterColorOptions = []
}) {
  const [searchText, setSearchText] = useState("");
  const [selectedSortColor, setSelectedSortColor] = useState("");
  const [selectedTextFilter, setSelectedTextFilter] = useState("");
  const [selectedFilterColor, setSelectedFilterColor] = useState("");

  const normalizedSelectedValues = pendingValues ?? selectedValues;

  const filteredValues = useMemo(() => {
    const query = searchText.toLowerCase();
    return values.filter((item) =>
      optionLabel(item)
        .toLowerCase()
        .includes(query)
    );
  }, [values, searchText]);

  const allValues = useMemo(() => {
    return values.map(optionValue);
  }, [values]);

  const selectedValueSet = useMemo(
    () => new Set(normalizedSelectedValues),
    [normalizedSelectedValues]
  );
  const isAllSelected =
    allValues.length > 0 &&
    allValues.every((value) => selectedValueSet.has(value));

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

    if (selectedValueSet.has(normalized)) {
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
    <div className={oaTableFilterDropdownStyles.wrapper}>
      {hasAnyTopOption && (
        <div className={oaTableFilterDropdownStyles.topSection}>
          {hasSortAsc && (
            <button
              type="button"
              onClick={onSortAsc}
              className={oaTableFilterDropdownStyles.actionButton}
            >
              <ArrowDownAZ size={13} />
              <span>Ascending</span>
            </button>
          )}

          {hasSortDesc && (
            <button
              type="button"
              onClick={onSortDesc}
              className={oaTableFilterDropdownStyles.actionButton}
            >
              <ArrowUpAZ size={13} />
              <span>Descending</span>
            </button>
          )}

          {onToggleConditionalFormatting && (
            <button type="button" onClick={onToggleConditionalFormatting} aria-pressed={conditionalFormatting}

              className={oaTableFilterDropdownStyles.actionButton}>
              <Palette size={13} />
              <span>Conditional formatting</span>
              {conditionalFormatting ? <Check size={13} /> : null}
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
              className={oaTableFilterDropdownStyles.clearColumnButton}
            >
              <X size={13} />
              <span className="truncate">Clear Filter from "{columnName}"</span>
            </button>
          )}
        </div>
      )}

      <div className={oaTableFilterDropdownStyles.searchSection}>
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

      <FilterValueList key={searchText} values={filteredValues}
        selectedValueSet={selectedValueSet} toggleValue={toggleValue}
        toggleAll={toggleAll} isAllSelected={isAllSelected} />

      <div className={oaTableFilterDropdownStyles.footer}>
        <button
          type="button"
          onClick={onCancel}
          className={oaTableFilterDropdownStyles.cancelButton}
          aria-label="Cancel filter"

        >
          <X size={14} />
        </button>

        <button
          type="button"
          onClick={handleApply}
          className={oaTableFilterDropdownStyles.applyButton}
          aria-label="Apply filter"

        >
          <Check size={14} />
        </button>
      </div>
    </div>
  );
}
