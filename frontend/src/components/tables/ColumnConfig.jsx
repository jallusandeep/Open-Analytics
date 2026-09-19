import { useId, useState } from "react";
import { Check, Columns3, GripVertical, ListChecks, ListX, Plus, Save, X } from "lucide-react";
import Modal from "../common/Modal";
import { oaCheckboxControlStyles } from "../common/uiStyles";
import IconButton from "../common/IconButton";
import Select from "../common/Select";
import Input from "../common/Input";
import Tooltip from "../common/Tooltip";

function storageKey(columns, tableId) {
  let userId = "guest";
  try {
    const user = JSON.parse(sessionStorage.getItem("open_analytics_current_user") || sessionStorage.getItem("open_analytics_user") || "null");
    userId = user?.user_id || user?.login_id || user?.email || user?.username || "guest";
  } catch { /* The default view remains available without session storage. */ }
  return `oa-table-view:v1:${JSON.stringify([userId, tableId || window.location.pathname + window.location.search, columns.map((column) => column.key)])}`;
}

function readViews(key, columns) {
  const fallback = { views: [], activeId: "default", defaultId: "default" };
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    const clean = (keys) => Array.isArray(keys) ? [...new Set(keys)].filter((key) => columns.some((column) => column.key === key)) : [];
    if (Array.isArray(value?.columns)) {
      const keys = clean(value.columns);
      return keys.length ? { views: [{ id: "legacy", name: "My view", columns: keys }], activeId: value.active ? "legacy" : "default", defaultId: value.active ? "legacy" : "default" } : fallback;
    }
    const views = Array.isArray(value?.views) ? value.views.filter((view) => typeof view?.id === "string" && view.id !== "default" && typeof view.name === "string").map((view) => ({ ...view, columns: clean(view.columns) })).filter((view) => view.columns.length) : [];
    const preferredId = value?.defaultId ?? value?.activeId;
    const defaultId = views.some((view) => view.id === preferredId) ? preferredId : "default";
    return { views, activeId: defaultId, defaultId };
  } catch { return fallback; }
}

function ColumnConfigState({ columns, children, viewKey, configOpen, onConfigClose }) {
  const nameInputId = useId();
  const allKeys = columns.map((column) => column.key);
  const [saved, setSaved] = useState(() => readViews(viewKey, columns));
  const initialKeys = saved.views.find((view) => view.id === saved.activeId)?.columns || allKeys;
  const [selected, setSelected] = useState(initialKeys);
  const [draft, setDraft] = useState(initialKeys);
  const [viewId, setViewId] = useState(saved.activeId);
  const [makeDefault, setMakeDefault] = useState(true);
  const [localOpen, setLocalOpen] = useState(false);
  const open = configOpen ?? localOpen;
  const [draggedKey, setDraggedKey] = useState(null);
  const [search, setSearch] = useState("");
  const [selectedSearch, setSelectedSearch] = useState("");
  const [error, setError] = useState("");
  const [naming, setNaming] = useState(false);
  const [viewName, setViewName] = useState("");
  const [status, setStatus] = useState("");

  function persist(value) {
    try {
      localStorage.setItem(viewKey, JSON.stringify(value));
      setSaved(value);
      setError("");
      return true;
    } catch {
      setError("Your browser could not save this view. You can still apply columns for this session.");
      return false;
    }
  }

  function close() {
    setLocalOpen(false);
    onConfigClose?.();
    setDraft(selected);
    setViewId(saved.activeId);
    setMakeDefault(saved.activeId === saved.defaultId);
    setNaming(false);
    setSearch("");
    setSelectedSearch("");
    setError("");
    setStatus("");
  }

  function moveColumn(key, targetKey) {
    if (key === targetKey) return;
    setDraft((previous) => {
      const from = previous.indexOf(key);
      const to = previous.indexOf(targetKey);
      if (from < 0 || to < 0) return previous;
      const next = [...previous];
      next.splice(from, 1);
      next.splice(to, 0, key);
      return next;
    });
    setStatus("");
  }

  function saveNewView() {
    if (!naming) {
      setNaming(true);
      setViewId("new");
      setViewName("");
      return;
    }
    const name = viewName.trim();
    if (!name) { setError("Enter a name for the new view."); return; }
    if (name.toLowerCase() === "default view" || saved.views.some((view) => view.name.toLowerCase() === name.toLowerCase())) {
      setError("A view with this name already exists. Choose a different name."); return;
    }
    const id = crypto.randomUUID();
    if (persist({ views: [...saved.views, { id, name, columns: draft }], activeId: id, defaultId: makeDefault ? id : saved.defaultId })) {
      setSelected(draft);
      setViewId(id);
      setNaming(false);
      setStatus(`Saved ${name}${makeDefault ? " as your default view" : ""}.`);
    }
  }

  const visibleOptions = columns.filter((column) => String(column.label).toLowerCase().includes(search.toLowerCase()));
  const visibleSelected = draft.filter((key) => String(columns.find((column) => column.key === key)?.label).toLowerCase().includes(selectedSearch.toLowerCase()));
  return <div className="flex h-full min-h-0 w-full min-w-0 flex-col">
    {configOpen === undefined && <div className="flex shrink-0 border-b border-oa-border bg-black px-3 py-1.5">
      <IconButton icon={Columns3} label="Column config" disabled={!columns.length} onClick={() => setLocalOpen(true)} />
    </div>}
    <div className="min-h-0 flex-1">{children(selected.map((key) => columns.find((column) => column.key === key)).filter(Boolean))}</div>
    <Modal open={open} title="Column config" onClose={close} width="max-w-4xl" footer={<>
      <IconButton icon={X} label="Close" variant="filterCancel" size="filter" tooltipSide="top" onClick={close} />
      <IconButton icon={Check} label="Apply columns" variant="filterApply" size="filter" disabled={!draft.length} onClick={() => {
        const original = viewId === "default" ? allKeys : saved.views.find((view) => view.id === viewId)?.columns;
        const matches = original?.length === draft.length && original.every((key, index) => key === draft[index]);
        if (makeDefault && !matches) { setError("Save these column changes as a new view to make them your default."); return; }
        const defaultId = makeDefault ? viewId : saved.defaultId === viewId ? "default" : saved.defaultId;
        if (matches && !persist({ ...saved, activeId: viewId, defaultId })) return;
        setSelected(draft); setLocalOpen(false); onConfigClose?.(); setNaming(false); setError(""); setStatus("");
      }} />
      <IconButton icon={Save} label={naming ? "Save new view" : "Save as new view"} variant="add" size="filter" disabled={!draft.length} onClick={saveNewView} />
    </>}>
      <div className="oa-app-font max-h-[70vh] space-y-3 overflow-y-auto">
        <div className="flex items-end gap-2">
          <div className="min-w-0 flex-1 space-y-1"><label className="text-xs text-oa-muted">View</label>
            <Select ariaLabel="Table view" minWidth="w-full" value={viewId} options={[{ value: "default", label: "Default view" }, ...saved.views.map((view) => ({ value: view.id, label: `${view.name}${view.id === saved.defaultId ? " (My default)" : ""}` })), ...(naming ? [{ value: "new", label: "New view" }] : [])]} onChange={(event) => {
              const id = event.target.value;
              if (id === "new") return;
              setViewId(id); setMakeDefault(id === saved.defaultId); setDraft(id === "default" ? allKeys : saved.views.find((view) => view.id === id).columns); setNaming(false); setError(""); setStatus("");
            }} />
          </div>
          <IconButton icon={Plus} label="Add view" variant="add" onClick={() => { setNaming(true); setViewId("new"); setMakeDefault(false); setViewName(""); setDraft(allKeys); setError(""); setStatus(""); }} />
        </div>
        <label className={oaCheckboxControlStyles.wrapper}>
          <input type="checkbox" className={oaCheckboxControlStyles.checkbox} checked={makeDefault} onChange={(event) => { setMakeDefault(event.target.checked); setError(""); }} />
          <span>Make this my default view</span>
        </label>
        {naming && <div className="space-y-1"><label htmlFor={nameInputId} className="text-xs text-oa-muted">New view name</label><Input id={nameInputId} autoFocus maxLength={80} placeholder="Name your view" value={viewName} onChange={(event) => setViewName(event.target.value)} /></div>}
        <div className="grid gap-3 md:grid-cols-2">
          <section className="min-w-0 p-3">
            <div className="mb-2 flex h-8 items-center justify-between gap-2"><h3 className="text-xs font-semibold">All columns</h3><div className="flex gap-1">
              <IconButton icon={ListChecks} label="Select all columns" onClick={() => setDraft([...draft, ...allKeys.filter((key) => !draft.includes(key))])} />
              <IconButton icon={ListX} label="Clear selection" variant="danger" onClick={() => setDraft([])} />
            </div></div>
            <Input aria-label="Search columns" placeholder="Search columns" value={search} onChange={(event) => setSearch(event.target.value)} />
            <div className="mt-2 max-h-[38vh] space-y-1 overflow-y-auto rounded border border-oa-border p-1">
              {visibleOptions.map((column) => <label key={column.key} className={oaCheckboxControlStyles.wrapper}>
                <input type="checkbox" className={oaCheckboxControlStyles.checkbox} checked={draft.includes(column.key)} onChange={(event) => { setDraft(event.target.checked ? [...draft, column.key] : draft.filter((key) => key !== column.key)); setStatus(""); }} />
                <span className={oaCheckboxControlStyles.label}>{column.label}</span>
              </label>)}
              {!visibleOptions.length && <p className="p-2 text-xs text-oa-muted">No columns match your search.</p>}
            </div>
          </section>
          <section className="min-w-0 p-3">
            <h3 className="mb-2 flex h-8 items-center text-xs font-semibold">Selected columns ({draft.length})</h3>
            <Input aria-label="Search selected columns" placeholder="Search selected columns" value={selectedSearch} onChange={(event) => setSelectedSearch(event.target.value)} />
            <ol className="mt-2 max-h-[38vh] space-y-1 overflow-y-auto rounded border border-oa-border p-1">
              {visibleSelected.map((key) => {
                const index = draft.indexOf(key);
                const label = columns.find((column) => column.key === key)?.label;
                return <li key={key} draggable onDragStart={(event) => { setDraggedKey(key); event.dataTransfer.setData("text/plain", key); event.dataTransfer.effectAllowed = "move"; }} onDragEnd={() => setDraggedKey(null)} onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = "move"; }} onDrop={(event) => { event.preventDefault(); if (draggedKey) moveColumn(draggedKey, key); setDraggedKey(null); }} className={`flex h-8 items-center gap-2 rounded border px-3 font-mono text-xs tracking-[-0.01em] ${draggedKey === key ? "border-blue-500 bg-blue-500/15" : "border-oa-border bg-black"}`}>
                  <GripVertical size={14} className="shrink-0 cursor-grab text-blue-400" /><span className="min-w-0 flex-1 truncate" title={String(label)}>{label}</span>
                  <Select ariaLabel={`Position of ${label}`} className="[&>button]:h-6" minWidth="w-16" value={String(index)} options={draft.map((_, position) => ({ value: String(position), label: String(position + 1) }))} onChange={(event) => moveColumn(key, draft[Number(event.target.value)])} />
                  <Tooltip text={`Remove ${label}`} side="top">
                    <button type="button" aria-label={`Remove ${label}`} onClick={() => setDraft(draft.filter((item) => item !== key))} className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-oa-muted transition hover:bg-oa-card hover:text-white">
                      <X size={13} />
                    </button>
                  </Tooltip>
                </li>;
              })}
            </ol>
            {draft.length > 0 && !visibleSelected.length && <p className="p-2 text-xs text-oa-muted">No selected columns match your search.</p>}
            {!draft.length && <p role="status" className="py-3 text-xs text-amber-300">Select at least one column from the left.</p>}
          </section>
        </div>
        {error && <p role="alert" className="text-xs text-red-300">{error}</p>}
        {status && <p role="status" className="text-xs text-emerald-300">{status}</p>}
      </div>
    </Modal>
  </div>;
}

export default function ColumnConfig({ columns, tableId, children, configOpen, onConfigClose }) {
  const key = storageKey(columns, tableId);
  return <ColumnConfigState key={key} viewKey={key} columns={columns} configOpen={configOpen} onConfigClose={onConfigClose}>{children}</ColumnConfigState>;
}
