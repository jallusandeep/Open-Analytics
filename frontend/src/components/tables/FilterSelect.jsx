import { X } from "lucide-react";

import Select from "../common/Select";

function FilterSelect({
  value,
  onChange,
  options,
  onClear,
  showClear = false,
  ariaLabel,
  minWidth = "w-36"
}) {
  return (
    <div className="relative">
      <Select
        value={value}
        onChange={onChange}
        options={options}
        ariaLabel={ariaLabel}
        minWidth={minWidth}
      />

      {showClear && (
        <button
          type="button"
          onClick={onClear}
          className="absolute -right-2 -top-2 flex h-4 w-4 items-center justify-center rounded-full border border-oa-border bg-black text-oa-muted shadow transition hover:bg-oa-card hover:text-white"
          aria-label={`Clear ${ariaLabel}`}
          title={`Clear ${ariaLabel}`}
        >
          <X size={9} />
        </button>
      )}
    </div>
  );
}

export default FilterSelect;
