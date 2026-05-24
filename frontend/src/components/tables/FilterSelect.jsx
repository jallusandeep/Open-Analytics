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
          className="absolute -right-2 -top-2 flex h-4 w-4 items-center justify-center rounded-full border border-oa-border bg-black text-red-400 shadow transition hover:border-red-500/60 hover:bg-red-950/40 hover:text-red-300"
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
