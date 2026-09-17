export const referenceViews = [
  { value: "securities", label: "Securities" },
  { value: "listings", label: "Exchange Listings" },
  { value: "indices", label: "Index Membership" },
  { value: "identifiers", label: "Identifier History" }
];
export function referencePageUrl(view) {
  return `/reference-data?view=${encodeURIComponent(view)}`;
}
