import SearchBox from "../common/SearchBox";

function FilterSearchInput({
  value,
  onChange,
  onClear,
  placeholder = "Search users"
}) {
  return (
    <SearchBox
      value={value}
      onChange={onChange}
      onClear={onClear}
      placeholder={placeholder}
    />
  );
}

export default FilterSearchInput;
