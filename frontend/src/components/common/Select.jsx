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
        className={`flex h-8 w-full items-center justify-between gap-2 rounded border border-oa-border bg-black px-2 text-xs text-oa-text outline-none transition hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500 ${
          open ? "border-blue-500 bg-oa-card" : ""
        }`}
      >
        <span className="truncate">{selectedOption?.label || "Select"}</span>

        <ChevronDown
          size={12}
          className={`shrink-0 text-oa-muted transition duration-150 ${
            open ? "rotate-180 text-sky-300" : ""
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
                  className={`relative flex h-8 w-full items-center justify-between rounded-sm border-l px-2 text-left text-xs transition ${
                    selected
                      ? "border-l-sky-400 bg-sky-950/30 text-white"
                      : "border-l-transparent text-oa-muted hover:border-l-oa-border hover:bg-oa-card/70 hover:text-white"
                  }`}
                >
                  <span className="truncate">{option.label}</span>

                  {selected && (
                    <Check size={12} className="shrink-0 text-sky-300" />
                  )}
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