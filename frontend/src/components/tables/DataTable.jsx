import { cloneElement, isValidElement, useEffect, useRef, useState } from "react";
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
  fitToViewport = false,
  resizableColumns = false,
  getRowKey,
  renderCell,
  renderActions,
  filterConfig
}) {
  const headerRef = useRef(null);
  const dragCleanupRef = useRef(null);
  const [columnWidths, setColumnWidths] = useState(null);
  const [formattedColumns, setFormattedColumns] = useState({});
  function formattingKey(column) {
    return `${columns.map((item) => item.key).join("|")}:${column.key}`;
  }
  function numericValue(value) {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    if (typeof value !== "string" || !value.trim()) return null;
    const clean = value.trim().replace(/,/g, "").replace(/%$/, "");
    if (!/^-?\d+(\.\d+)?$/.test(clean)) return null;
    return Number(clean);
  }
  function numericCellValue(row, column) {
    if (!fitToViewport || /(^|_)(id|key|isin|symbol|code|date|timestamp|year|period)(_|$)/i.test(column.key)) return null;
    return numericValue(row[column.key]);
  }
  function renderDisplayCell(row, column) {
    const rendered = renderCell(row, column);
    const number = numericCellValue(row, column);
    if (number === null) return rendered;
    const text = number.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) +
      (typeof row[column.key] === "string" && row[column.key].trim().endsWith("%") ? "%" : "");
    return isValidElement(rendered) && rendered.type === "span"
      ? cloneElement(rendered, {}, text)
      : text;
  }
  function cellFormatting(row, column) {
    if (!formattedColumns[formattingKey(column)]) return "";
    const number = numericValue(row[column.key]);
    return number > 0 ? " bg-emerald-500/15 !text-emerald-300" : number < 0 ? " bg-red-500/15 !text-red-300" : "";
  }
  const columnSignature = `${columns.map((column) => column.key).join("|")}:${gridTemplateColumns}:${Boolean(renderActions)}`;
  const resizedWidths = columnWidths?.signature === columnSignature ? columnWidths.widths : null;

  useEffect(() => () => dragCleanupRef.current?.(), []);

  function resizeColumn(index, delta) {
    const widths = resizedWidths || Array.from(headerRef.current.children).map((cell) => cell.getBoundingClientRect().width);
    setColumnWidths({ signature: columnSignature, widths: widths.map((width, position) => position === index ? Math.max(80, width + delta) : width) });
  }

  function startResize(event, index) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    dragCleanupRef.current?.();
    const widths = Array.from(headerRef.current.children).map((cell) => cell.getBoundingClientRect().width);
    const startX = event.clientX;
    const handle = event.currentTarget;
    handle.setPointerCapture(event.pointerId);
    function move(pointerEvent) {
      setColumnWidths({ signature: columnSignature, widths: widths.map((width, position) => position === index ? Math.max(80, width + pointerEvent.clientX - startX) : width) });
    }
    function cleanup() {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", cleanup);
      handle.removeEventListener("pointercancel", cleanup);
      handle.removeEventListener("lostpointercapture", cleanup);
      dragCleanupRef.current = null;
    }
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", cleanup);
    handle.addEventListener("pointercancel", cleanup);
    handle.addEventListener("lostpointercapture", cleanup);
    dragCleanupRef.current = cleanup;
  }
  const compactDataRowClass = `${oaTableStyles.dataRow} !py-1`;
  const resolvedGridTemplateColumns = getResolvedGridTemplateColumns(
    gridTemplateColumns,
    columns.length,
    Boolean(renderActions)
  );
  const responsiveGridTemplateColumns = fitToViewport
    ? splitGridTemplateColumns(resolvedGridTemplateColumns).map((column) => {
        const pixels = column.match(/^(\d+(?:\.\d+)?)px$/);
        const fraction = column.match(/^(\d+(?:\.\d+)?)fr$/);
        const weight = pixels ? Number(pixels[1]) / 160 : fraction ? Number(fraction[1]) : 1;
        return `minmax(0, ${weight}fr)`;
      }).join(" ")
    : resolvedGridTemplateColumns;
  const fixedGridWidth = resizedWidths ? resizedWidths.reduce((total, width) => total + width, 0) : fitToViewport ? null : getFixedGridWidth(resolvedGridTemplateColumns);
  const tableWidthClass = fixedGridWidth ? "w-max" : fitToViewport ? "w-full min-w-0" : `w-full ${minWidth}`;
  const tableSurfaceStyle = fixedGridWidth
    ? {
        width: `${fixedGridWidth}px`,
        maxWidth: "none"
      }
    : undefined;
  const gridStyle = { gridTemplateColumns: resizedWidths ? resizedWidths.map((width) => `${width}px`).join(" ") : responsiveGridTemplateColumns };

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
      <div role="status" aria-live="polite" className="sticky left-0 flex min-h-[260px] w-full max-w-full items-center justify-center px-3">
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
            ref={headerRef}
            className={`${oaTableStyles.headerRow} ${oaTableStyles.headerText} sticky top-0 z-10 !rounded-none border-b border-oa-border`}
            style={gridStyle}
          >
            {columns.map((column) => {
              const active =
                filterConfig?.isColumnFilterActive?.(column.key) || false;

              const open = filterConfig?.activeFilter === column.key;

              return (
                <div key={column.key} className={getHeaderCellClass(column)}>
                  <span title={column.label} className={oaTableStyles.headerLabel}>
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
                      conditionalFormatting={Boolean(formattedColumns[formattingKey(column)])}
                      onToggleConditionalFormatting={rows.some((row) => numericValue(row[column.key]) !== null) || formattedColumns[formattingKey(column)] ? () => {
                        const key = formattingKey(column);
                        setFormattedColumns((previous) => ({ ...previous, [key]: !previous[key] }));
                      } : undefined}
                    />
                  )}
                  {resizableColumns && (
                    <button
                      type="button"
                      aria-label={`Resize ${column.label} column`}
                      title="Drag to resize · Arrow keys to adjust · Double-click to reset widths"
                      onPointerDown={(event) => startResize(event, columns.indexOf(column))}
                      onDoubleClick={() => setColumnWidths(null)}
                      onKeyDown={(event) => {
                        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
                          event.preventDefault();
                          resizeColumn(columns.indexOf(column), event.key === "ArrowLeft" ? -16 : 16);
                        }
                      }}
                      className="absolute inset-y-0 right-0 z-20 w-2 touch-none cursor-col-resize border-r border-white/10 bg-transparent hover:border-white hover:bg-white/10 focus-visible:bg-white/20 focus-visible:outline-none"
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

          {!loading && rows.length > 0 ? (
            rows.map((row, rowIndex) => (
              <div
                key={getRowKey ? getRowKey(row, rowIndex) : rowIndex}
                className={`${compactDataRowClass} ${oaTableStyles.dataText}`}
                style={gridStyle}
              >
                {columns.map((column) => (
                  <div key={column.key} title={typeof row[column.key] === "string" || typeof row[column.key] === "number" ? String(row[column.key]) : undefined} className={`${oaTableStyles.dataCell}${cellFormatting(row, column)}${numericCellValue(row, column) !== null ? " text-right tabular-nums" : ""}`}>
                    {renderDisplayCell(row, column)}
                  </div>
                ))}

                {renderActions && (
                  <div className={oaTableStyles.actionCell}>
                    {renderActions(row)}
                  </div>
                )}
              </div>
            ))
          ) : null}
        </div>
        {loading ? renderStateMessage("loading") : rows.length === 0 ? renderStateMessage("empty") : null}
      </div>
    </div>
  );
}

export default DataTable;
