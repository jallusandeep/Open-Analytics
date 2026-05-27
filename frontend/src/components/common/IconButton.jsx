import Tooltip from "./Tooltip";
import { oaIconButtonStyles } from "./uiStyles";

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
        disabled={disabled}
        aria-label={label}
        className={`${oaIconButtonStyles.base} ${finalButtonClass}`}
      >
        {Icon && <Icon size={14} className={selectedIconClass} />}
      </button>
    </Tooltip>
  );
}

export default IconButton;