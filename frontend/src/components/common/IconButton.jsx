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
      "border-oa-border bg-black hover:bg-oa-card hover:border-oa-border",
    primary:
      "border-oa-border bg-white hover:bg-zinc-200",
    add:
      "border-oa-border bg-black hover:bg-oa-card",
    refresh:
      "border-oa-border bg-black hover:bg-oa-card",
    search:
      "border-oa-border bg-black hover:bg-oa-card",
    filter:
      "border-oa-border bg-black hover:bg-oa-card",
    danger:
      "border-oa-border bg-black hover:bg-red-950/40 hover:border-red-500/60"
  };

  const selectedButtonClass = buttonClass[variant] || buttonClass.default;
  const selectedIconClass = iconClass[variant] || iconClass.default;

  const finalButtonClass = active
    ? "border-oa-border bg-oa-card"
    : selectedButtonClass;

  const finalIconClass = active ? "text-white" : selectedIconClass;

  return (
    <Tooltip text={label} side={tooltipSide}>
      <button
        type={type}
        onClick={onClick}
        disabled={disabled}
        aria-label={label}
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded border transition disabled:cursor-not-allowed disabled:opacity-40 ${finalButtonClass}`}
      >
        {Icon && <Icon size={14} className={finalIconClass} />}
      </button>
    </Tooltip>
  );
}

export default IconButton;