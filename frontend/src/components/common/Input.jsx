function Input({ className = "", ...props }) {
  return (
    <input
      className={`h-8 rounded border border-oa-border bg-oa-card px-2 text-xs outline-none ${className}`}
      {...props}
    />
  );
}

export default Input;
