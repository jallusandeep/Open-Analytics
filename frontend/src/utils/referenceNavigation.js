export const referenceViews = [
  { value: "types", label: "Security Type Mapping" },
  { value: "listings", label: "Exchange Listings" },
  { value: "securities", label: "Securities" },
  { value: "indices", label: "Index Membership" },
  { value: "identifiers", label: "Identifier History" }
];
export function referencePageUrl(view) {
  return `/reference-data?view=${encodeURIComponent(view)}`;
}
