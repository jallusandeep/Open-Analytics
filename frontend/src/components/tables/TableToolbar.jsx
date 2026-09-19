import { Columns3, Search, X } from "lucide-react";

import IconButton from "../common/IconButton";
import FilterSearchInput from "./FilterSearchInput";
import FilterSelect from "./FilterSelect";

function TableToolbar({
  searchValue,
  onSearchChange,
  onSearchClear,
  onSearchSubmit,
  searchActive = false,
  searchPlaceholder = "Search users",
  filters = [],
  hasActiveFilter = false,
  onClearAll,
  loading = false,
  rightActions = [],
  onColumnConfig,
  trailingContent = null
}) {
  return (
    <form
      onSubmit={onSearchSubmit}
      className="flex flex-wrap items-center gap-2"
    >
      <FilterSearchInput
        value={searchValue}
        onChange={onSearchChange}
        onClear={onSearchClear}
        placeholder={searchPlaceholder}
        active={searchActive}
      />

      {filters.map((filter) => (
        <FilterSelect
          key={filter.ariaLabel}
          value={filter.value}
          onChange={filter.onChange}
          options={filter.options}
          onClear={filter.onClear}
          showClear={filter.showClear}
          ariaLabel={filter.ariaLabel}
          minWidth={filter.minWidth || "w-36"}
        />
      ))}

      <IconButton
        icon={Search}
        label="Search"
        type="submit"
        variant="search"
        tooltipSide="top"
        disabled={loading}
      />

      {hasActiveFilter && (
        <IconButton
          icon={X}
          label="Clear filters"
          type="button"
          variant="danger"
          tooltipSide="top"
          onClick={onClearAll}
        />
      )}

      {(rightActions.length > 0 || onColumnConfig) && (
        <div className="flex items-center gap-2">
          {rightActions.map((action) => (
            <IconButton
              key={action.label}
              icon={action.icon}
              label={action.label}
              type="button"
              variant={action.variant || "default"}
              tooltipSide={action.tooltipSide || "top"}
              disabled={action.disabled}
              onClick={action.onClick}
            />
          ))}
          {onColumnConfig && <IconButton icon={Columns3} label="Column config" tooltipSide="top" disabled={loading} onClick={onColumnConfig} />}
        </div>
      )}
      {trailingContent}
    </form>
  );
}

export default TableToolbar;
