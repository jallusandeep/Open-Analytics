import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

import { oaSelectStyles } from "./uiStyles";

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
    <div
      ref={wrapperRef}
      className={`${oaSelectStyles.wrapper} ${minWidth} ${className}`}
    >
      <button
        type="button"
        aria-label={ariaLabel}
        onClick={() => setOpen((previous) => !previous)}
        className={`${oaSelectStyles.button} ${
          open
            ? `${oaSelectStyles.buttonOpen} !border-sky-500/70 shadow-[0_0_0_1px_rgba(14,165,233,0.25)]`
            : "hover:border-sky-500/40"
        }`}
      >
        <span className="truncate">{selectedOption?.label || "Select"}</span>

        <ChevronDown
          size={12}
          className={`${oaSelectStyles.chevron} ${
            open ? `${oaSelectStyles.chevronOpen} text-sky-300` : ""
          }`}
        />
      </button>

      {open && (
        <div className={`${oaSelectStyles.menu} !border-sky-500/50`}>
          <div className={oaSelectStyles.menuScroll}>
            {options.map((option) => {
              const selected = option.value === value;

              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handleSelect(option.value)}
                  className={`${oaSelectStyles.option} ${
                    selected
                      ? oaSelectStyles.optionSelected
                      : oaSelectStyles.optionDefault
                  }`}
                >
                  <span className="truncate">{option.label}</span>

                  {selected && (
                    <Check size={12} className={oaSelectStyles.optionCheck} />
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