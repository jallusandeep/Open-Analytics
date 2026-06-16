import Spinner from "../common/Spinner";
import { oaTableStyles } from "../common/uiStyles";
import DataTableHeaderFilter from "./DataTableHeaderFilter";

const DEFAULT_ACTION_COLUMN_WIDTH = "96px";

function splitGridTemplateColumns(gridTemplateColumns) {
  if (!gridTemplateColumns) {
    return [];
  }

  const columns = [];
  let currentColumn = "";
  let depth = 0;

  for (const character of gridTemplateColumns.trim()) {
    if (character === "(") {
      depth += 1;
    } else if (character === ")") {
      depth = Math.max(0, depth - 1);
    }

    if (/\s/.test(character) && depth === 0) {
      if (currentColumn) {
        columns.push(currentColumn);
        currentColumn = "";
      }
    } else {
      currentColumn += character;
    }
  }

  if (currentColumn) {
    columns.push(currentColumn);
  }

  return columns;
}

function getResolvedGridTemplateColumns(gridTemplateColumns, columnCount, hasActions) {
  const gridColumns = splitGridTemplateColumns(gridTemplateColumns);

  if (!hasActions || gridColumns.length !== columnCount) {
    return gridTemplateColumns;
  }

  return `${gridTemplateColumns} ${DEFAULT_ACTION_COLUMN_WIDTH}`;
}

function getFixedGridWidth(gridTemplateColumns) {
  const gridColumns = splitGridTemplateColumns(gridTemplateColumns);

  if (gridColumns.length === 0) {
    return null;
  }

  let totalWidth = 0;

  for (const column of gridColumns) {
    const match = column.match(/^(\d+(?:\.\d+)?)px$/);

    if (!match) {
      return null;
    }

    totalWidth += Number(match[1]);
  }

  return totalWidth;
}

function DataTable({
  columns,
  rows,
  loading = false,
  loadingMessage = "Loading",
  emptyMessage = "No records found.",
  gridTemplateColumns,
  minWidth = "min-w-full",
  getRowKey,
  renderCell,
  renderActions,
  filterConfig
}) {
  const compactDataRowClass = `${oaTableStyles.dataRow} !py-1`;
  const resolvedGridTemplateColumns = getResolvedGridTemplateColumns(
    gridTemplateColumns,
    columns.length,
    Boolean(renderActions)
  );
  const fixedGridWidth = getFixedGridWidth(resolvedGridTemplateColumns);
  const tableWidthClass = fixedGridWidth ? "w-max" : `w-full ${minWidth}`;
  const tableSurfaceStyle = fixedGridWidth
    ? {
        width: `${fixedGridWidth}px`,
        maxWidth: "none"
      }
    : undefined;
  const gridStyle = { gridTemplateColumns: resolvedGridTemplateColumns };

  function isFilterEnabled(column) {
    if (!filterConfig) {
      return false;
    }

    if (filterConfig.enabled === false) {
      return false;
    }

    if (column.filterable === false) {
      return false;
    }

    return true;
  }

  function getFilterAlign(column) {
    if (filterConfig?.rightAlignedKeys?.includes(column.key)) {
      return "right";
    }

    return "left";
  }

  function getHeaderCellClass(column) {
    return isFilterEnabled(column)
      ? oaTableStyles.headerCell
      : oaTableStyles.headerCellNoFilter;
  }

  function renderStateMessage(type) {
    const isLoading = type === "loading";

    return (
      <div className="sticky left-0 flex min-h-[260px] w-full max-w-full items-center justify-center px-3">
        <div
          className={`flex items-center justify-center gap-2 text-center ${
            isLoading ? oaTableStyles.mutedText : oaTableStyles.emptyText
          }`}
        >
          {isLoading && <Spinner size="sm" color="light" />}
          <span>{isLoading ? loadingMessage : emptyMessage}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`${oaTableStyles.wrapper} relative z-0 min-h-0 !rounded-none`}>
      <div className="min-h-0 overflow-visible !rounded-none">
        <div className={tableWidthClass} style={tableSurfaceStyle}>
          <div
            className={`${oaTableStyles.headerRow} ${oaTableStyles.headerText} sticky top-0 z-10 !rounded-none border-b border-oa-border`}
            style={gridStyle}
          >
            {columns.map((column) => {
              const active =
                filterConfig?.isColumnFilterActive?.(column.key) || false;

              const open = filterConfig?.activeFilter === column.key;

              return (
                <div key={column.key} className={getHeaderCellClass(column)}>
                  <span className={oaTableStyles.headerLabel}>
                    {column.label}
                  </span>

                  {isFilterEnabled(column) && (
                    <DataTableHeaderFilter
                      column={column}
                      active={active}
                      open={open}
                      align={getFilterAlign(column)}
                      values={filterConfig?.headerValues?.[column.key] || []}
                      selectedValues={
                        filterConfig?.columnFilters?.[column.key] || []
                      }
                      pendingValues={
                        filterConfig?.draftColumnFilters?.[column.key] || []
                      }
                      onOpen={() => filterConfig?.onOpen?.(column.key)}
                      onClose={() => filterConfig?.onClose?.()}
                      onChange={(values) =>
                        filterConfig?.onChange?.(column.key, values)
                      }
                      onApply={() => filterConfig?.onApply?.(column.key)}
                      onCancel={() => filterConfig?.onClose?.()}
                      onSortAsc={() =>
                        filterConfig?.onSort?.(column.key, "asc")
                      }
                      onSortDesc={() =>
                        filterConfig?.onSort?.(column.key, "desc")
                      }
                      onClear={() => filterConfig?.onClear?.(column.key)}
                    />
                  )}
                </div>
              );
            })}

            {renderActions && (
              <div className={oaTableStyles.actionHeader}>
                <span className={oaTableStyles.actionHeaderLabel}>Action</span>
              </div>
            )}
          </div>

          {loading ? (
            renderStateMessage("loading")
          ) : rows.length === 0 ? (
            renderStateMessage("empty")
          ) : (
            rows.map((row, rowIndex) => (
              <div
                key={getRowKey ? getRowKey(row, rowIndex) : rowIndex}
                className={`${compactDataRowClass} ${oaTableStyles.dataText}`}
                style={gridStyle}
              >
                {columns.map((column) => (
                  <div key={column.key} className={oaTableStyles.dataCell}>
                    {renderCell(row, column)}
                  </div>
                ))}

                {renderActions && (
                  <div className={oaTableStyles.actionCell}>
                    {renderActions(row)}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default DataTable;
