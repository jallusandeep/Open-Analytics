import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { createPortal } from "react-dom";

import { oaSelectStyles } from "./uiStyles";

function Select({
  name,
  value,
  onChange,
  options = [],
  className = "",
  ariaLabel = "Select",
  minWidth = "w-36",
  disabled = false
}) {
  const [open, setOpen] = useState(false);
  const [menuDirection, setMenuDirection] = useState("down");
  const [menuMaxHeight, setMenuMaxHeight] = useState(240);
  const wrapperRef = useRef(null);
  const buttonRef = useRef(null);
  const menuRef = useRef(null);
  const [menuPosition, setMenuPosition] = useState({ left: 0, top: 0, width: 0 });

  const selectedOption =
    options.find((option) => option.value === value) || options[0];

  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target) && !menuRef.current?.contains(event.target)) {
        setOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    function handleWindowChange() {
      if (open) {
        updateMenuPosition();
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    window.addEventListener("resize", handleWindowChange);
    window.addEventListener("scroll", handleWindowChange, true);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
      window.removeEventListener("resize", handleWindowChange);
      window.removeEventListener("scroll", handleWindowChange, true);
    };
  }, [open]);

  useLayoutEffect(() => {
    if (open) {
      updateMenuPosition();
    }
  }, [open, options.length]);

  function updateMenuPosition() {
    if (!buttonRef.current) {
      return;
    }

    const rect = buttonRef.current.getBoundingClientRect();
    const viewportHeight =
      window.innerHeight || document.documentElement.clientHeight;
    const gap = 0;
    const safePadding = 12;
    const preferredHeight = Math.min(240, Math.max(120, options.length * 34 + 8));

    const spaceBelow = viewportHeight - rect.bottom - safePadding;
    const spaceAbove = rect.top - safePadding;

    if (spaceBelow >= preferredHeight || spaceBelow >= spaceAbove) {
      setMenuDirection("down");
      setMenuPosition({ left: rect.left, top: rect.bottom, width: rect.width });
      setMenuMaxHeight(Math.max(96, Math.min(preferredHeight, spaceBelow - gap)));
      return;
    }

    setMenuDirection("up");
    setMenuPosition({ left: rect.left, bottom: viewportHeight - rect.top, width: rect.width });
    setMenuMaxHeight(Math.max(96, Math.min(preferredHeight, spaceAbove - gap)));
  }

  function handleSelect(optionValue) {
    onChange({
      target: {
        name,
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
        ref={buttonRef}
        type="button"
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={() => setOpen((previous) => !previous)}
        className={`${oaSelectStyles.button} ${
          open
            ? `${oaSelectStyles.buttonOpen} !border-sky-500/70 shadow-[0_0_0_1px_rgba(14,165,233,0.25)]`
            : "hover:border-sky-500/40"
        } ${
          disabled ? "cursor-not-allowed opacity-60 hover:border-oa-border" : ""
        }`}
      >
        <span className="truncate">{selectedOption?.label || "Select"}</span>

        <ChevronDown
          size={12}
          className={`${oaSelectStyles.chevron} ${
            open
              ? `${oaSelectStyles.chevronOpen} text-sky-300 ${
                  menuDirection === "up" ? "rotate-180" : ""
                }`
              : ""
          }`}
        />
      </button>

      {open ? createPortal(
        <div
          ref={menuRef}
          style={{ position: "fixed", left: menuPosition.left, top: menuPosition.top ?? "auto", bottom: menuPosition.bottom ?? "auto", width: menuPosition.width, zIndex: 1000 }}
          className={`${oaSelectStyles.menu} !border-sky-500/50 ${menuDirection === "down" ? "origin-top animate-[oaSelectDown_0.1s_ease-out]" : "origin-bottom animate-[oaMenuIn_0.1s_ease-out]"}`}
        >
          <div
            className={oaSelectStyles.menuScroll}
            style={{ maxHeight: `${menuMaxHeight}px` }}
          >
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

                  {selected ? (
                    <Check size={12} className={oaSelectStyles.optionCheck} />
                  ) : null}
                </button>
              );
            })}
          </div>
        </div>
      , document.body) : null}
    </div>
  );
}

export default Select;
