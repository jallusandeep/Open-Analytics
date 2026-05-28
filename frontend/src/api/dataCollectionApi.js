import axiosClient from "./axiosClient";

export function getUpstoxDataCollectionSummary() {
  return axiosClient.get("/data-collection/upstox/summary");
}

export function getUpstoxDataCollectionRuns() {
  return axiosClient.get("/data-collection/upstox/runs");
}

export function getUpstoxInstrumentsPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/instruments", {
    params
  });
}

export function getUpstoxExpiredInstrumentsPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/expired-instruments", {
    params
  });
}

export function syncUpstoxCurrentInstruments(config = {}) {
  return axiosClient.post("/data-collection/upstox/sync-current", null, config);
}

export function syncUpstoxAllInstruments(config = {}) {
  return axiosClient.post("/data-collection/upstox/sync-all", null, config);
}

export function cancelUpstoxDataCollection() {
  return axiosClient.post("/data-collection/upstox/cancel");
}

export function syncUpstoxExpiredInstruments(config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/sync-expired-default",
    null,
    config
  );
}
