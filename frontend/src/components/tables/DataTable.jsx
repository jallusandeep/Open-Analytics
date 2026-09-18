import { cloneElement, isValidElement, useEffect, useRef, useState } from "react";
import ScreenLoading from "../common/ScreenLoading";
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

  if (!hasActions) {
    return gridTemplateColumns;
  }
  if (gridColumns.length === columnCount + 1) {
    const actionWidth = gridColumns.pop();
    return [actionWidth, ...gridColumns].join(" ");
  }
  return `${DEFAULT_ACTION_COLUMN_WIDTH} ${gridTemplateColumns}`;
}

function DataTable({
  columns,
  rows,
  loading = false,
  loadingMessage = "Loading",
  loadingPlacement = "screen",
  stateMessageMinHeight = 260,
  emptyMessage = "No records found.",
  gridTemplateColumns,
  minWidth = "min-w-full",
  fitToViewport = false,
  resizableColumns = false,
  wrapHeaders = false,
  getRowKey,
  renderCell,
  renderActions,
  filterConfig
}) {
  const headerRef = useRef(null);
  const horizontalScrollRef = useRef(null);
  const horizontalScrollProxyRef = useRef(null);
  const tableSurfaceRef = useRef(null);
  const dragCleanupRef = useRef(null);
  const [columnWidths, setColumnWidths] = useState(null);
  const [formattedColumns, setFormattedColumns] = useState({});
  const [horizontalScroll, setHorizontalScroll] = useState({ visible: false, width: 0 });
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

  useEffect(() => {
    const scrollArea = horizontalScrollRef.current;
    const surface = tableSurfaceRef.current;
    if (!scrollArea || !surface || loading) {
      setHorizontalScroll({ visible: false, width: 0 });
      return undefined;
    }
    const update = () => setHorizontalScroll({
      visible: surface.scrollWidth > scrollArea.clientWidth + 1,
      width: surface.scrollWidth
    });
    update();
    const observer = new ResizeObserver(update);
    observer.observe(scrollArea);
    observer.observe(surface);
    return () => observer.disconnect();
  }, [columnSignature, loading, resizedWidths, rows.length]);

  function syncHorizontalScroll(source, target) {
    if (target && Math.abs(target.scrollLeft - source.scrollLeft) > 1) {
      target.scrollLeft = source.scrollLeft;
    }
  }

  function resizeColumn(index, delta) {
    const widths = resizedWidths || measureColumnWidths();
    setColumnWidths({ signature: columnSignature, widths: widths.map((width, position) => position === index ? Math.max(80, width + delta) : width) });
  }

  function startResize(event, index) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    dragCleanupRef.current?.();
    const widths = measureColumnWidths();
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
  function measureColumnWidths() {
    const cells = Array.from(headerRef.current.children);
    if (renderActions) cells.unshift(cells.pop());
    return cells.map((cell) => cell.getBoundingClientRect().width);
  }
  const compactDataRowClass = `${oaTableStyles.dataRow} !py-1`;
  const resolvedGridTemplateColumns = getResolvedGridTemplateColumns(
    gridTemplateColumns,
    columns.length,
    Boolean(renderActions)
  );
  const gridTracks = splitGridTemplateColumns(resolvedGridTemplateColumns);
  const visualColumns = renderActions ? [{ label: "Action", filterable: false }, ...columns] : columns;
  const minimumWidths = visualColumns.map((column, index) => {
    const track = gridTracks[index] || "1fr";
    const labelWidth = Math.ceil(String(column.label).length * 8.5 + (isFilterEnabled(column) ? 64 : 36));
    const fixedWidth = !fitToViewport && /^(\d+(?:\.\d+)?)px$/.exec(track);
    return Math.max(80, labelWidth, fixedWidth ? Number(fixedWidth[1]) : 0);
  });
  const responsiveGridTemplateColumns = gridTracks
    .map((column, index) => {
        const pixels = column.match(/^(\d+(?:\.\d+)?)px$/);
        const fraction = column.match(/^(\d+(?:\.\d+)?)fr$/);
        const weight = pixels ? Number(pixels[1]) / 160 : fraction ? Number(fraction[1]) : 1;
        return `minmax(${minimumWidths[index] || 80}px, ${weight}fr)`;
      }).join(" ");
  const tableWidthClass = resizedWidths ? "w-max" : minWidth;
  const tableSurfaceStyle = resizedWidths
    ? { width: `${resizedWidths.reduce((total, width) => total + width, 0)}px`, maxWidth: "none" }
    : { width: `max(100%, ${minimumWidths.reduce((total, width) => total + width, 0)}px)` };
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

  function getColumnDividerClass(index) {
    return index > 0 || renderActions ? " border-l border-oa-border" : "";
  }

  function renderStateMessage(type) {
    const isLoading = type === "loading";

    if (isLoading && loadingPlacement === "screen") return <ScreenLoading message={loadingMessage} />;

    return (
      <div role="status" aria-live="polite" className={`${isLoading && loadingPlacement === "table" ? "absolute inset-0 z-20 bg-black/70" : "sticky left-0"} flex w-full max-w-full items-center justify-center px-3`} style={isLoading && loadingPlacement === "table" ? undefined : { minHeight: stateMessageMinHeight }}>
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
      <div ref={horizontalScrollRef} onScroll={(event) => syncHorizontalScroll(event.currentTarget, horizontalScrollProxyRef.current)} className={`oa-data-table-scroll min-h-0 !rounded-none ${loading ? "overflow-x-hidden" : "overflow-x-auto"}${horizontalScroll.visible ? " oa-data-table-scroll-source" : ""}`}>
        <div ref={tableSurfaceRef} className={tableWidthClass} style={tableSurfaceStyle}>
          <div
            ref={headerRef}
            className={`${oaTableStyles.headerRow} ${oaTableStyles.headerText} sticky top-0 z-10 !rounded-none border-b border-oa-border`}
            style={gridStyle}
          >
            {columns.map((column, columnIndex) => {
              const active =
                filterConfig?.isColumnFilterActive?.(column.key) || false;

              const open = filterConfig?.activeFilter === column.key;

              return (
                <div key={column.key} className={`${getHeaderCellClass(column)}${getColumnDividerClass(columnIndex)}`}>
                  <span  className={`${oaTableStyles.headerLabel}${wrapHeaders ? " !whitespace-normal !leading-4" : ""}`}>
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

                      onPointerDown={(event) => startResize(event, columns.indexOf(column) + (renderActions ? 1 : 0))}
                      onDoubleClick={() => setColumnWidths(null)}
                      onKeyDown={(event) => {
                        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
                          event.preventDefault();
                          resizeColumn(columns.indexOf(column) + (renderActions ? 1 : 0), event.key === "ArrowLeft" ? -16 : 16);
                        }
                      }}
                      className="absolute inset-y-0 right-0 z-20 w-2 touch-none cursor-col-resize border-r border-white/10 bg-transparent hover:border-white hover:bg-white/10 focus-visible:bg-white/20 focus-visible:outline-none"
                    />
                  )}
                </div>
              );
            })}

            {renderActions && (
              <div className={`${oaTableStyles.actionHeader} -order-1 !justify-start`}>
                <span className={oaTableStyles.actionHeaderLabel}>Action</span>
              </div>
            )}
          </div>

          {(!loading || loadingPlacement === "table") && rows.length > 0 ? (
            rows.map((row, rowIndex) => (
              <div
                key={getRowKey ? getRowKey(row, rowIndex) : rowIndex}
                className={`${compactDataRowClass} ${oaTableStyles.dataText}${loading && loadingPlacement === "table" ? " invisible" : ""}`}
                style={gridStyle}
              >
                {columns.map((column, columnIndex) => (
                  <div key={column.key}  className={`${oaTableStyles.dataCell}${getColumnDividerClass(columnIndex)}${cellFormatting(row, column)}${numericCellValue(row, column) !== null ? " text-right tabular-nums" : ""}`}>
                    {renderDisplayCell(row, column)}
                  </div>
                ))}

                {renderActions && (
                  <div className={`${oaTableStyles.actionCell} -order-1 !justify-start`}>
                    {renderActions(row)}
                  </div>
                )}
              </div>
            ))
          ) : null}
        </div>
        {loading && loadingPlacement === "table" && rows.length === 0 && <div aria-hidden="true" style={{ height: stateMessageMinHeight }} />}
        {loading ? renderStateMessage("loading") : rows.length === 0 ? renderStateMessage("empty") : null}
      </div>
      {horizontalScroll.visible && !loading ? (
        <div ref={horizontalScrollProxyRef} onScroll={(event) => syncHorizontalScroll(event.currentTarget, horizontalScrollRef.current)} className="oa-data-table-scroll sticky bottom-0 z-30 h-[12px] overflow-x-auto overflow-y-hidden border-t border-oa-border bg-black" aria-label="Horizontal table scroll">
          <div aria-hidden="true" className="h-px" style={{ width: `${horizontalScroll.width}px` }} />
        </div>
      ) : null}
    </div>
  );
}

export default DataTable;
