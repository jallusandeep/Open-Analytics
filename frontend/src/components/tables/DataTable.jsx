import Spinner from "../common/Spinner";
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
    <div className="overflow-hidden rounded border border-oa-border bg-black oa-table-font">
      <div className={minWidth}>
        <div
          className="grid border-b border-oa-border bg-oa-panel px-3 py-2.5 text-[11px] font-bold uppercase tracking-wider text-oa-muted"
          style={{ gridTemplateColumns }}
        >
          {columns.map((column) => {
            const active =
              filterConfig?.isColumnFilterActive?.(column.key) || false;

            const open = filterConfig?.activeFilter === column.key;

            return (
              <div
                key={column.key}
                className="relative flex min-w-0 items-center justify-between gap-2 pr-8"
              >
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
                    onSortAsc={() => filterConfig?.onSort?.(column.key, "asc")}
                    onSortDesc={() =>
                      filterConfig?.onSort?.(column.key, "desc")
                    }
                    onClear={() => filterConfig?.onClear?.(column.key)}
                  />
                )}
              </div>
            );
          })}

          {renderActions && <span className="text-center">Action</span>}
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 px-3 py-8 text-xs text-oa-muted">
            <Spinner size="sm" color="light" />
            {loadingMessage}
          </div>
        ) : rows.length === 0 ? (
          <div className="px-3 py-8 text-center text-xs text-oa-muted">
            {emptyMessage}
          </div>
        ) : (
          rows.map((row, rowIndex) => (
            <div
              key={getRowKey ? getRowKey(row) : rowIndex}
              className="grid items-center border-b border-oa-border px-3 py-2 text-[13px] last:border-b-0 hover:bg-oa-panel/60"
              style={{ gridTemplateColumns }}
            >
              {columns.map((column) => renderCell(row, column))}

              {renderActions && (
                <span className="flex justify-center">
                  {renderActions(row)}
                </span>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default DataTable;
