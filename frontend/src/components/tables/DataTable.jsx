import Spinner from "../common/Spinner";
import { oaTableStyles } from "../common/uiStyles";
import DataTableHeaderFilter from "./DataTableHeaderFilter";

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
        <div className={`w-full ${minWidth}`}>
          <div
            className={`${oaTableStyles.headerRow} ${oaTableStyles.headerText} sticky top-0 z-10 !rounded-none border-b border-oa-border`}
            style={{ gridTemplateColumns }}
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
                style={{ gridTemplateColumns }}
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