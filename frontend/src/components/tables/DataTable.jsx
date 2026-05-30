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
  minWidth = "min-w-[1080px]",
  getRowKey,
  renderCell,
  renderActions,
  filterConfig
}) {
  const solidHeaderBg = "bg-[#121316]";
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
    const baseClass = isFilterEnabled(column)
      ? oaTableStyles.headerCell
      : oaTableStyles.headerCellNoFilter;

    return `${baseClass} ${solidHeaderBg}`;
  }

  function renderStateMessage(type) {
    const isLoading = type === "loading";

    return (
      <div className="sticky left-0 flex min-h-[260px] w-[calc(100vw-96px)] max-w-full items-center justify-center px-3">
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
    <div className={`${oaTableStyles.wrapper} relative z-0 min-h-0`}>
      <div className="min-h-0 overflow-visible rounded">
        <div className={minWidth}>
          <div
            className={`${oaTableStyles.headerRow} ${oaTableStyles.headerText} ${solidHeaderBg} sticky top-0 z-10 rounded-t border-b border-oa-border shadow-[0_1px_0_rgba(255,255,255,0.04)]`}
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
              <div className={`${oaTableStyles.actionHeader} ${solidHeaderBg}`}>
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