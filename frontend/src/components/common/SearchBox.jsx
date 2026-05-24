import { Search } from "lucide-react";
import { useState } from "react";

function SearchBox({
  value,
  onChange,
  placeholder = "Search",
  className = "",
  inputClassName = "",
  iconSize = 14,
  active = false
}) {
  const [focused, setFocused] = useState(false);
  const selected = focused || active;

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

      {active && (
        <span
          className="pointer-events-none absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border border-black bg-sky-400 shadow"
          aria-hidden="true"
          title="Search active"
        />
      )}
    </div>
  );
}

export default SearchBox;
