import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

function Select({
  value,
  onChange,
  options = [],
  className = "",
  ariaLabel = "Select",
  minWidth = "w-36"
}) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef(null);

  const selectedOption =
    options.find((option) => option.value === value) || options[0];

  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSelect(optionValue) {
    onChange({
      target: {
        value: optionValue
      }
    });

    setOpen(false);
  }

  return (
    <div ref={wrapperRef} className={`relative ${minWidth} ${className}`}>
      <button
        type="button"
        aria-label={ariaLabel}
        onClick={() => setOpen((previous) => !previous)}
        className={`flex h-8 w-full items-center justify-between gap-2 rounded border border-oa-border bg-black px-2 text-xs text-oa-text transition hover:bg-oa-card ${
          open ? "bg-oa-card" : ""
        }`}
      >
        <span className="truncate">
          {selectedOption?.label || "Select"}
        </span>

        <ChevronDown
          size={12}
          className={`shrink-0 text-oa-muted transition duration-150 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {open && (
        <div className="absolute left-0 top-9 z-50 w-full min-w-[150px] overflow-hidden rounded border border-oa-border bg-black p-1 shadow-2xl animate-[oaMenuIn_0.14s_ease-out]">
          <div className="max-h-64 overflow-y-auto">
            {options.map((option) => {
              const selected = option.value === value;

              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handleSelect(option.value)}
                  className={`flex h-8 w-full items-center justify-between rounded-sm px-2 text-left text-xs transition hover:bg-oa-card ${
                    selected ? "bg-oa-card text-white" : "text-oa-muted"
                  }`}
                >
                  <span className="truncate">{option.label}</span>
                  {selected && <Check size={12} />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default Select;