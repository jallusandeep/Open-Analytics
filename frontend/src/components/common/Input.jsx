function Input({ className = "", ...props }) {
  return (
    <input
      className={`h-8 w-full rounded border border-oa-border bg-black px-3 text-xs text-white outline-none placeholder:text-oa-muted focus:border-blue-500 ${className || ""}`}
      {...props}
    />
  );
}

export default Input;
