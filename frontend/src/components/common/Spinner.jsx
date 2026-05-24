function Spinner({ size = "sm", color = "dark" }) {
  const sizeClass = {
    xs: "h-3 w-3",
    sm: "h-4 w-4",
    md: "h-5 w-5",
    lg: "h-6 w-6"
  };

  const colorClass = {
    dark: "border-black border-t-transparent",
    light: "border-white border-t-transparent",
    muted: "border-oa-muted border-t-transparent"
  };

  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 ${sizeClass[size]} ${colorClass[color]}`}
    />
  );
}

export default Spinner;