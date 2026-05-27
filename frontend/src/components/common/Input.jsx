import { oaInputStyles } from "./uiStyles";

function Input({ className = "", ...props }) {
  return (
    <input
      className={`${oaInputStyles.base} ${className || ""}`}
      {...props}
    />
  );
}

export default Input;