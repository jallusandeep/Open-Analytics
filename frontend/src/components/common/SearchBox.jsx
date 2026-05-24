import { Search, X } from "lucide-react";

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
  return (
    <div
      className={`relative flex h-8 w-[360px] max-w-full items-center gap-2 rounded border border-oa-border bg-black px-2 focus-within:border-blue-500 ${className}`}
    >
      <Search size={iconSize} className="text-oa-muted" />

      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className={`w-full bg-transparent pr-6 text-xs text-white outline-none placeholder:text-oa-muted ${inputClassName}`}
      />

      {String(value || "").trim() !== "" && (
        <button
          type="button"
          onClick={onClear}
          className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded-sm border border-oa-border bg-black text-oa-muted transition hover:bg-oa-card hover:text-white"
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
