export const oaTableStyles = {
  wrapper: "relative rounded border border-oa-border bg-black oa-table-font",
  inner: "overflow-visible rounded",
  headerRow:
    "grid rounded-t border-b border-oa-border bg-oa-panel px-3 py-2.5",
  headerText:
    "font-mono text-[11px] font-bold uppercase tracking-[0.12em] text-oa-muted",
  headerCell:
    "relative flex min-w-0 items-center justify-between gap-2 pr-8",
  dataRow:
    "grid items-center border-b border-oa-border px-3 py-2 last:border-b-0 hover:bg-oa-panel/60",
  dataText: "font-mono text-[13px] font-medium tracking-[-0.01em] text-oa-text",
  mutedText: "font-mono text-xs text-oa-muted",
  emptyText: "font-mono text-xs text-oa-muted",
  actionHeader:
    "text-center font-mono text-[11px] font-bold uppercase tracking-[0.12em] text-oa-muted",
  actionCell: "flex justify-center"
};

export const oaCardStyles = {
  wrapper: "rounded border border-oa-border bg-black",
  header: "border-b border-oa-border bg-oa-panel px-4 py-3",

  headerTitle:
    "font-mono text-[13px] font-semibold uppercase tracking-[0.08em] text-white",
  headerSubtitle: "font-mono text-[11px] font-medium tracking-[-0.01em] text-oa-muted",
  body: "block truncate font-mono text-[13px] font-semibold tracking-[-0.01em] text-white",
  bodyMuted: "font-mono text-[12px] tracking-[-0.01em] text-oa-muted",

  modalTitle: "font-mono text-[14px] font-semibold tracking-[-0.01em] text-white",
  modalSubtitle: "font-mono text-[11px] tracking-[-0.01em] text-oa-muted",
  modalBody: "font-mono text-[13px] tracking-[-0.01em] text-oa-text"
};

export const oaToolbarStyles = {
  wrapper: "mb-3 flex flex-wrap items-center gap-2",
  rightActions: "ml-auto flex items-center gap-2"
};

export const oaSearchBoxStyles = {
  wrapper:
    "relative flex h-8 w-[360px] max-w-full items-center gap-2 rounded border px-2 outline-none transition",
  wrapperDefault:
    "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card",
  wrapperFocused: "border-blue-500 bg-black",
  icon: "text-oa-muted",
  iconFocused: "text-sky-300",
  input:
    "w-full bg-transparent pr-6 font-mono text-xs tracking-[-0.01em] text-white outline-none placeholder:text-oa-muted",
  clearButton:
    "absolute right-2 top-1/2 flex h-4 w-4 -translate-y-1/2 items-center justify-center rounded-sm text-oa-muted transition hover:bg-oa-card hover:text-white",
  activeDot:
    "pointer-events-none absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border border-black bg-sky-400 shadow"
};

export const oaFilterSelectStyles = {
  wrapper: "relative",
  activeDot:
    "pointer-events-none absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border border-black bg-sky-400 shadow"
};

export const oaSelectStyles = {
  wrapper: "relative",
  button:
    "flex h-8 w-full items-center justify-between gap-2 rounded border border-oa-border bg-black px-2 font-mono text-xs tracking-[-0.01em] text-oa-text outline-none transition hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500",
  buttonOpen: "border-blue-500 bg-oa-card",
  chevron: "shrink-0 text-oa-muted transition duration-150",
  chevronOpen: "rotate-180 text-sky-300",
  menu:
    "absolute left-0 top-9 z-50 w-full min-w-[150px] overflow-hidden rounded border border-oa-border bg-black p-1 shadow-2xl animate-[oaMenuIn_0.14s_ease-out]",
  menuScroll: "max-h-64 overflow-y-auto",
  option:
    "relative flex h-8 w-full items-center justify-between rounded-sm border-l px-2 text-left font-mono text-xs tracking-[-0.01em] transition",
  optionSelected: "border-l-sky-400 bg-sky-950/30 text-white",
  optionDefault:
    "border-l-transparent text-oa-muted hover:border-l-oa-border hover:bg-oa-card/70 hover:text-white",
  optionCheck: "shrink-0 text-sky-300"
};

export const oaInputStyles = {
  base:
    "h-8 w-full rounded border border-oa-border bg-black px-3 font-mono text-xs tracking-[-0.01em] text-white outline-none placeholder:text-oa-muted transition focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
};

export const oaIconButtonStyles = {
  base:
    "flex h-8 w-8 shrink-0 items-center justify-center rounded border outline-none transition disabled:cursor-not-allowed disabled:opacity-40",

  variantIcon: {
    default: "text-oa-muted",
    primary: "text-black",
    add: "text-emerald-300",
    refresh: "text-amber-300",
    search: "text-sky-300",
    filter: "text-indigo-300",
    danger: "text-red-400"
  },

  variantButton: {
    default:
      "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500",
    primary:
      "border-oa-border bg-white hover:border-sky-500/40 hover:bg-zinc-200 focus:border-blue-500",
    add:
      "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500",
    refresh:
      "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500",
    search:
      "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500",
    filter:
      "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500",
    danger:
      "border-oa-border bg-black hover:border-red-500/60 hover:bg-red-950/40 focus:border-red-500"
  },

  variantActive: {
    default: "border-blue-500 bg-oa-card",
    primary: "border-blue-500 bg-white",
    add: "border-blue-500 bg-oa-card",
    refresh: "border-blue-500 bg-oa-card",
    search: "border-blue-500 bg-oa-card",
    filter: "border-blue-500 bg-oa-card",
    danger: "border-red-500 bg-red-950/40"
  }
};

export const oaHeaderFilterStyles = {
  button:
    "absolute right-3 top-1/2 flex h-[22px] w-[22px] -translate-y-1/2 items-center justify-center rounded-sm border outline-none transition",
  buttonDefault:
    "border-oa-border bg-black text-oa-muted hover:border-sky-500/40 hover:bg-oa-card hover:text-white",
  buttonSelected: "border-blue-500 bg-sky-950/30 text-sky-300",
  activeDot:
    "absolute -right-1 -top-1 h-2 w-2 rounded-full border border-black bg-emerald-400",
  portal: "fixed z-[9999]"
};

export const oaTableFilterDropdownStyles = {
  wrapper:
    "w-[310px] max-w-[calc(100vw-32px)] overflow-visible rounded border border-oa-border bg-black font-mono text-oa-text shadow-2xl animate-[oaMenuIn_0.14s_ease-out]",
  topSection: "py-1",

  actionButton:
    "flex h-8 w-full items-center gap-2 px-3 text-left text-xs normal-case tracking-[-0.01em] text-oa-muted transition hover:bg-oa-card hover:text-white",

  menuButton:
    "flex h-8 w-full items-center justify-between px-3 text-left text-xs normal-case tracking-[-0.01em] transition",
  menuButtonDefault: "text-oa-muted hover:bg-oa-card hover:text-white",
  menuButtonActive: "bg-oa-card text-white",
  menuButtonLeft: "flex items-center gap-2",

  flyoutWrapper: "group relative",
  flyoutMenu:
    "absolute top-0 z-[70] hidden overflow-hidden rounded border border-oa-border bg-black shadow-2xl group-hover:block",
  flyoutNormal: "w-44",
  flyoutWide: "w-48",
  flyoutOption:
    "flex h-8 w-full items-center justify-between gap-2 px-3 text-left text-xs normal-case tracking-[-0.01em] transition",
  flyoutOptionDefault: "text-oa-muted hover:bg-oa-card hover:text-white",
  flyoutOptionActive: "bg-sky-950/30 text-white",

  selectedDot: "h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400",

  clearColumnButton:
    "flex h-8 w-full items-center gap-2 px-3 text-left text-xs normal-case tracking-[-0.01em] text-red-400 transition hover:bg-red-950/40 hover:text-red-300",

  searchSection: "border-y border-oa-border p-2",
  valuesSection: "max-h-56 overflow-y-auto p-1",

  valueButton:
    "flex h-8 w-full items-center gap-2 rounded-sm px-2 text-left text-xs normal-case tracking-[-0.01em] text-oa-muted transition hover:bg-oa-card hover:text-white",
  valueRow:
    "flex h-8 w-full items-center justify-between gap-2 rounded-sm px-2 text-left text-xs normal-case tracking-[-0.01em] transition",
  valueRowDefault: "text-oa-muted hover:bg-oa-card hover:text-white",
  valueRowSelected: "bg-oa-card/70 text-white",
  valueLeft: "flex min-w-0 items-center gap-2",
  valueCount: "shrink-0 text-[10px] tracking-[-0.01em] text-oa-muted",

  checkbox:
    "flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border",
  checkboxChecked: "border-white bg-white text-black",
  checkboxUnchecked: "border-oa-border bg-black text-transparent",

  emptyValues:
    "px-2 py-3 text-center text-[11px] normal-case tracking-[-0.01em] text-oa-muted",

  footer:
    "flex items-center justify-end gap-2 border-t border-oa-border px-2 py-2",
  cancelButton:
    "flex h-7 w-7 items-center justify-center rounded-sm border border-oa-border bg-black text-red-400 transition hover:border-red-500/60 hover:bg-red-950/40 hover:text-red-300",
  applyButton:
    "flex h-7 w-7 items-center justify-center rounded-sm border border-oa-border bg-black text-emerald-300 transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500"
};

export const oaFormTextStyles = {
  label: "font-mono text-[12px] font-medium tracking-[-0.01em] text-oa-muted",
  value: "font-mono text-[13px] font-medium tracking-[-0.01em] text-oa-text",
  helper: "font-mono text-[12px] tracking-[-0.01em] text-oa-muted",
  error: "font-mono text-[12px] font-medium tracking-[-0.01em] text-red-400"
};

export const oaPillStyles = {
  base:
    "rounded-full border px-2.5 py-0.5 font-mono text-[11px] font-medium tracking-[-0.01em]"
};