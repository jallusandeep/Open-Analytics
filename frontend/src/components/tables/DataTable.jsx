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

  return (
    <div className={oaTableStyles.wrapper}>
      <div className={oaTableStyles.inner}>
        <div className={minWidth}>
          <div
            className={`${oaTableStyles.headerRow} ${oaTableStyles.headerText}`}
            style={{ gridTemplateColumns }}
          >
            {columns.map((column) => {
              const active =
                filterConfig?.isColumnFilterActive?.(column.key) || false;

              const open = filterConfig?.activeFilter === column.key;

              return (
                <div key={column.key} className={oaTableStyles.headerCell}>
                  <span className="truncate">{column.label}</span>

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
              <span className={oaTableStyles.actionHeader}>Action</span>
            )}
          </div>

          {loading ? (
            <div
              className={`flex items-center justify-center gap-2 px-3 py-8 ${oaTableStyles.mutedText}`}
            >
              <Spinner size="sm" color="light" />
              {loadingMessage}
            </div>
          ) : rows.length === 0 ? (
            <div
              className={`px-3 py-8 text-center ${oaTableStyles.emptyText}`}
            >
              {emptyMessage}
            </div>
          ) : (
            rows.map((row, rowIndex) => (
              <div
                key={getRowKey ? getRowKey(row) : rowIndex}
                className={`${oaTableStyles.dataRow} ${oaTableStyles.dataText}`}
                style={{ gridTemplateColumns }}
              >
                {columns.map((column) => renderCell(row, column))}

                {renderActions && (
                  <span className={oaTableStyles.actionCell}>
                    {renderActions(row)}
                  </span>
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