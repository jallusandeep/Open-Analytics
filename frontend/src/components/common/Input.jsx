function Input({ className = "", ...props }) {
  return (
    <input
      className={`h-9 w-full rounded border border-oa-border bg-black px-3 text-[13px] text-white outline-none placeholder:text-oa-muted focus:border-blue-500 focus:ring-1 focus:ring-blue-500 ${className || ""}`}
      {...props}
    />
  );
}

export default Input;
