export const referenceViews = [
  { value: "types", label: "Security Type Mapping" },
  { value: "listings", label: "Exchange Listings" },
  { value: "securities", label: "Securities Metadata" }
];
export function referencePageUrl(view) {
  return `/reference-data?view=${encodeURIComponent(view)}`;
}
