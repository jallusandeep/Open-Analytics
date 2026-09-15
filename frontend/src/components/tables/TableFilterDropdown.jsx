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
import { oaTableFilterDropdownStyles } from "../common/uiStyles";

function normalizeValue(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }

  return String(value);
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
  pendingValues = [],
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

  function getCheckboxClassName(checked) {
    return checked
      ? oaTableFilterDropdownStyles.checkboxChecked
      : oaTableFilterDropdownStyles.checkboxUnchecked;
  }

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

      <div className={oaTableFilterDropdownStyles.valuesSection}>
        <button
          type="button"
          onClick={toggleAll}
          className={oaTableFilterDropdownStyles.valueButton}
        >
          <span
            className={`${oaTableFilterDropdownStyles.checkbox} ${getCheckboxClassName(
              isAllSelected
            )}`}
          >
            <Check size={11} />
          </span>

          <span className="truncate">(Select All)</span>
        </button>

        {filteredValues.length === 0 ? (
          <div className={oaTableFilterDropdownStyles.emptyValues}>
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
                className={`${oaTableFilterDropdownStyles.valueRow} ${
                  selected
                    ? oaTableFilterDropdownStyles.valueRowSelected
                    : oaTableFilterDropdownStyles.valueRowDefault
                }`}
              >
                <span className={oaTableFilterDropdownStyles.valueLeft}>
                  <span
                    className={`${oaTableFilterDropdownStyles.checkbox} ${getCheckboxClassName(
                      selected
                    )}`}
                  >
                    <Check size={11} />
                  </span>

                  <span className="truncate">{label}</span>
                </span>

                {item.count !== undefined && (
                  <span className={oaTableFilterDropdownStyles.valueCount}>
                    {item.count}
                  </span>
                )}
              </button>
            );
          })
        )}
      </div>

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
