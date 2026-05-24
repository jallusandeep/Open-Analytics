import { Search, X } from "lucide-react";
import { useState } from "react";

function SearchBox({
  value,
  onChange,
  onClear,
  placeholder = "Search",
  className = "",
  inputClassName = "",
  iconSize = 14,
  clearIconSize = 11,
  clearLabel = "Clear search"
}) {
  const [focused, setFocused] = useState(false);
  const hasValue = String(value || "").trim() !== "";
  const selected = focused || hasValue;

  const wrapperStateClass = selected
    ? "border-blue-500 bg-black"
    : "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card";

  return (
    <div
      className={`relative flex h-8 w-[360px] max-w-full items-center gap-2 rounded border px-2 outline-none transition ${wrapperStateClass} ${className}`}
    >
      <Search
        size={iconSize}
        className={`shrink-0 transition ${
          selected ? "text-sky-300" : "text-oa-muted"
        }`}
      />

      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        className={`w-full bg-transparent pr-6 text-xs text-white outline-none placeholder:text-oa-muted ${inputClassName}`}
      />

      {hasValue && (
        <button
          type="button"
          onClick={onClear}
          className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded-sm border border-oa-border bg-black text-red-400 outline-none transition hover:border-red-500/60 hover:bg-red-950/40 hover:text-red-300 focus:border-red-500"
          aria-label={clearLabel}
          title={clearLabel}
        >
          <X size={clearIconSize} />
        </button>
      )}
    </div>
  );
}

export default SearchBox;