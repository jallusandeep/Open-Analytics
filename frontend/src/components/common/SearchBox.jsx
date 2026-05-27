import { Search, X } from "lucide-react";
import { useState } from "react";

import { oaSearchBoxStyles } from "./uiStyles";

function SearchBox({
  value,
  onChange,
  onClear,
  placeholder = "Search",
  className = "",
  inputClassName = "",
  iconSize = 14,
  active = false
}) {
  const [focused, setFocused] = useState(false);
  const selected = focused;

  const wrapperStateClass = selected
    ? oaSearchBoxStyles.wrapperFocused
    : oaSearchBoxStyles.wrapperDefault;

  function handleClear() {
    onClear?.();
  }

  return (
    <div
      className={`${oaSearchBoxStyles.wrapper} ${wrapperStateClass} ${className}`}
    >
      <Search
        size={iconSize}
        className={`shrink-0 transition ${
          selected ? oaSearchBoxStyles.iconFocused : oaSearchBoxStyles.icon
        }`}
      />

      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        className={`${oaSearchBoxStyles.input} ${inputClassName}`}
      />

      {value && (
        <button
          type="button"
          onClick={handleClear}
          className={oaSearchBoxStyles.clearButton}
          aria-label="Clear search"
        >
          <X size={12} />
        </button>
      )}

      {active && (
        <span
          className={oaSearchBoxStyles.activeDot}
          aria-hidden="true"
          title="Search active"
        />
      )}
    </div>
  );
}

export default SearchBox;