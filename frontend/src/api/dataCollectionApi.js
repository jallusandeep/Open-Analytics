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

export function getUpstoxOhlcvPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/ohlcv/preview", {
    params
  });
}

export function getUpstoxOhlcvOptions() {
  return axiosClient.get("/data-collection/upstox/ohlcv/options");
}

export function saveUpstoxOhlcvOptions(payload) {
  return axiosClient.put("/data-collection/upstox/ohlcv/options", payload);
}

export function syncUpstoxCurrentInstruments(config = {}) {
  return axiosClient.post("/data-collection/upstox/sync-current", null, config);
}

export function syncUpstoxExpiredInstruments(payload = {}, config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/sync-expired",
    payload,
    config
  );
}

export function syncUpstoxOhlcvDaily(payload = {}, config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/ohlcv/run",
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