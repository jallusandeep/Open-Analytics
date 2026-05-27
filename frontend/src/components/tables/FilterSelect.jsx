import Select from "../common/Select";
import { oaFilterSelectStyles } from "../common/uiStyles";

function FilterSelect({
  value,
  onChange,
  options,
  showClear = false,
  ariaLabel,
  minWidth = "w-36"
}) {
  return (
    <div className={oaFilterSelectStyles.wrapper}>
      <Select
        value={value}
        onChange={onChange}
        options={options}
        ariaLabel={ariaLabel}
        minWidth={minWidth}
      />

      {showClear && (
        <span
          className={oaFilterSelectStyles.activeDot}
          aria-hidden="true"
          title={`${ariaLabel} active`}
        />
      )}
    </div>
  );
}

export default FilterSelect;