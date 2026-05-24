import SearchBox from "../common/SearchBox";

function FilterSearchInput({
  value,
  onChange,
  onClear,
  placeholder = "Search users",
  active = false
}) {
  return (
    <SearchBox
      value={value}
      onChange={onChange}
      onClear={onClear}
      placeholder={placeholder}
      active={active}
    />
  );
}

export default FilterSearchInput;
