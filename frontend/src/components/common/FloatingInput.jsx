import { useCallback, useEffect, useId, useRef, useState } from "react";

function inputMatchesAutofill(input) {
  if (!input) {
    return false;
  }

  try {
    return input.matches(":-webkit-autofill") || input.matches(":autofill");
  } catch {
    return false;
  }
}

function FloatingInput({
  id,
  label,
  type = "text",
  value,
  onChange,
  icon: Icon,
  rightElement = null,
  autoComplete,
  disabled = false,
  error = "",
  className = "",
  inputClassName = "",
  name,
  required = false,
  variant = "form"
}) {
  const generatedId = useId();
  const inputId = id || generatedId;
  const inputRef = useRef(null);

  const [focused, setFocused] = useState(false);
  const [autofilled, setAutofilled] = useState(false);

  const isAuth = variant === "auth";
  const isUserModal = variant === "userModal";

  const wrapperClass = isAuth
    ? "h-12 rounded-lg px-3"
    : isUserModal
      ? "h-8 rounded px-3"
      : "h-8 rounded px-3";

  const inputTextClass = isAuth ? "text-sm" : "text-[12px]";
  const rightPaddingClass = rightElement ? "pr-8" : "";

  const syncAutofillValue = useCallback(
    (isAutofill, notifyChange = false) => {
      const input = inputRef.current;
      const domValue = input?.value ?? "";
      const detectedAutofill = isAutofill || inputMatchesAutofill(input);

      setAutofilled(Boolean(detectedAutofill && domValue));

      if (notifyChange && domValue && domValue !== String(value ?? "")) {
        onChange?.({
          target: input,
          currentTarget: input
        });
      }
    },
    [onChange, value]
  );

  useEffect(() => {
    const frameId = window.requestAnimationFrame(() =>
      syncAutofillValue(false, true)
    );

    const timeoutIds = [100, 500, 1000].map((delay) =>
      window.setTimeout(() => syncAutofillValue(false, true), delay)
    );

    return () => {
      window.cancelAnimationFrame(frameId);
      timeoutIds.forEach((timeoutId) => window.clearTimeout(timeoutId));
    };
  }, [syncAutofillValue]);

  return (
    <div className={`relative ${className}`}>
      {label && (
        <label
          htmlFor={inputId}
          className="mb-1.5 block text-[12px] font-medium tracking-wide text-oa-muted"
        >
          {label}
          {required && <span className="ml-1 text-red-400">*</span>}
        </label>
      )}

      <div
        data-autofilled={autofilled ? "true" : "false"}
        className={`relative flex ${wrapperClass} items-center gap-2 border bg-black transition-colors duration-200 ${
          error
            ? "border-red-500/70 focus-within:border-red-400"
            : "border-oa-border focus-within:border-oa-accent"
        } ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
      >
        {Icon && (
          <Icon
            size={16}
            className={`shrink-0 transition-colors duration-200 ${
              focused ? "text-oa-accent" : "text-oa-muted"
            }`}
          />
        )}

        <input
          ref={inputRef}
          id={inputId}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          onInput={() => setAutofilled(false)}
          onAnimationStart={(event) => {
            if (event.animationName === "oaAutofillStart") {
              syncAutofillValue(true, true);
            }

            if (event.animationName === "oaAutofillCancel") {
              syncAutofillValue(false);
            }
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          autoComplete={autoComplete}
          disabled={disabled}
          required={required}
          placeholder=""
          className={`oa-floating-input__control w-full bg-transparent text-oa-text outline-none placeholder:text-oa-muted disabled:cursor-not-allowed ${inputTextClass} ${rightPaddingClass} ${inputClassName}`}
        />

        {rightElement ? (
          <div className="absolute right-1.5 top-1/2 z-10 flex -translate-y-1/2 items-center">
            {rightElement}
          </div>
        ) : null}
      </div>

      {error && <p className="mt-1 text-[11px] text-red-400">{error}</p>}
    </div>
  );
}

export default FloatingInput;