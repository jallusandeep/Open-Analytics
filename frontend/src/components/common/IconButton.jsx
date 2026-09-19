import Tooltip from "./Tooltip";
import Spinner from "./Spinner";
import { oaIconButtonStyles } from "./uiStyles";

function IconButton({
  icon: Icon,
  label,
  onClick,
  type = "button",
  variant = "default",
  disabled = false,
  active = false,
  tooltipSide = "top",
  loading = false,
  form,
  iconSize = 14,
  size = "default",
  borderless = false
}) {
  const selectedBaseClass =
    size === "filter" ? oaIconButtonStyles.filterBase : oaIconButtonStyles.base;

  const selectedButtonClass =
    oaIconButtonStyles.variantButton[variant] ||
    oaIconButtonStyles.variantButton.default;

  const selectedIconClass =
    oaIconButtonStyles.variantIcon[variant] ||
    oaIconButtonStyles.variantIcon.default;

  const selectedActiveClass =
    oaIconButtonStyles.variantActive[variant] ||
    oaIconButtonStyles.variantActive.default;

  const finalButtonClass = active ? selectedActiveClass : selectedButtonClass;

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
        disabled={disabled || loading}
        form={form}
        aria-label={label}
        className={`${selectedBaseClass} ${finalButtonClass}${borderless ? " !border-0 !bg-transparent hover:!bg-red-500/15 hover:[&>svg]:text-red-300 hover:[&>svg]:scale-110 [&>svg]:transition-transform focus-visible:!bg-red-500/15" : ""}`}
      >
        {loading ? (
          <Spinner size="xs" color="light" />
        ) : (
          Icon && <Icon size={iconSize} className={selectedIconClass} />
        )}
      </button>
    </Tooltip>
  );
}

export default IconButton;
