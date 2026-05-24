import Tooltip from "./Tooltip";

function IconButton({
  icon: Icon,
  label,
  onClick,
  type = "button",
  variant = "default",
  disabled = false,
  active = false,
  tooltipSide = "top"
}) {
  const iconClass = {
    default: "text-oa-muted",
    primary: "text-black",
    add: "text-emerald-300",
    refresh: "text-amber-300",
    search: "text-sky-300",
    filter: "text-indigo-300",
    danger: "text-red-400"
  };

  const buttonClass = {
    default:
      "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500",
    primary:
      "border-oa-border bg-white hover:border-sky-500/40 hover:bg-zinc-200 focus:border-blue-500",
    add:
      "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500",
    refresh:
      "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500",
    search:
      "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500",
    filter:
      "border-oa-border bg-black hover:border-sky-500/40 hover:bg-oa-card focus:border-blue-500",
    danger:
      "border-oa-border bg-black hover:border-red-500/60 hover:bg-red-950/40 focus:border-red-500"
  };

  const activeButtonClass = {
    default: "border-blue-500 bg-oa-card",
    primary: "border-blue-500 bg-white",
    add: "border-blue-500 bg-oa-card",
    refresh: "border-blue-500 bg-oa-card",
    search: "border-blue-500 bg-oa-card",
    filter: "border-blue-500 bg-oa-card",
    danger: "border-red-500 bg-red-950/40"
  };

  const selectedButtonClass = buttonClass[variant] || buttonClass.default;
  const selectedIconClass = iconClass[variant] || iconClass.default;
  const selectedActiveClass =
    activeButtonClass[variant] || activeButtonClass.default;

  const finalButtonClass = active ? selectedActiveClass : selectedButtonClass;
  const finalIconClass = selectedIconClass;

  function handleClick(event) {
    onClick?.(event);

    if (variant === "refresh" || variant === "search") {
      event.currentTarget.blur();
    }
  }

  return (
    <Tooltip text={label} side={tooltipSide}>
      <button
        type={type}
        onClick={handleClick}
        disabled={disabled}
        aria-label={label}
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded border outline-none transition disabled:cursor-not-allowed disabled:opacity-40 ${finalButtonClass}`}
      >
        {Icon && <Icon size={14} className={finalIconClass} />}
      </button>
    </Tooltip>
  );
}

export default IconButton;