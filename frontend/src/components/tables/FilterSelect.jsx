import Select from "../common/Select";

function FilterSelect({
  value,
  onChange,
  options,
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
        <span
          className="pointer-events-none absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border border-black bg-sky-400 shadow"
          aria-hidden="true"
          title={`${ariaLabel} active`}
        />
      )}
    </div>
  );
}

export default FilterSelect;
