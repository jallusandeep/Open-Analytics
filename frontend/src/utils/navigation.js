export function dataPageUrl(view, subpage) {
  const params = new URLSearchParams({ view });
  if (subpage) params.set("subpage", subpage);
  return `/data?${params}`;
}
