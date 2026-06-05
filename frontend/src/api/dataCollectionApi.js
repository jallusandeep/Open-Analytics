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

export function getUpstoxOHLCVPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/ohlcv", {
    params
  });
}

export function syncUpstoxOHLCV() {
  return axiosClient.post(
    "/data-collection/upstox/sync-ohlcv"
  );
}

export function syncUpstoxExpiredInstruments(payload = {}, config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/sync-expired",
    payload,
    config
  );
}

export function cancelUpstoxDataCollection() {
  return axiosClient.post("/data-collection/upstox/cancel");
}

export function getUpstoxDataCollectionSchedules() {
  return axiosClient.get("/data-collection/upstox/schedules");
}

export function createUpstoxDataCollectionSchedule(payload) {
  return axiosClient.post("/data-collection/upstox/schedules", payload);
}

export function updateUpstoxDataCollectionSchedule(scheduleId, payload) {
  return axiosClient.put(
    `/data-collection/upstox/schedules/${scheduleId}`,
    payload
  );
}

export function toggleUpstoxDataCollectionSchedule(scheduleId) {
  return axiosClient.post(
    `/data-collection/upstox/schedules/${scheduleId}/toggle`
  );
}

export function deleteUpstoxDataCollectionSchedule(scheduleId) {
  return axiosClient.delete(`/data-collection/upstox/schedules/${scheduleId}`);
}