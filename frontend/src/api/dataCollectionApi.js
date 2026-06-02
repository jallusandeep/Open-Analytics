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

export function getUpstoxEquityInstrumentsPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/equity-instruments", {
    params
  });
}

export function getUpstoxOhlcvDailyPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/ohlcv-daily", {
    params
  });
}

export function getUpstoxEquityNewsPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/equity-news", {
    params
  });
}

export function getUpstoxFundamentalsPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/fundamentals", {
    params
  });
}

export function getUpstoxCorporateActionsPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/corporate-actions", {
    params
  });
}

export function getUpstoxFiiDiiActivityPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/fii-dii-activity", {
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

export function syncUpstoxEquityInstruments(config = {}) {
  return axiosClient.post("/data-collection/upstox/sync-equity", null, config);
}

export function syncUpstoxOhlcvDaily(params = {}, config = {}) {
  return axiosClient.post("/data-collection/upstox/sync-ohlcv-daily", null, {
    ...config,
    params
  });
}

export function syncUpstoxEquityNews(config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/sync-equity-news",
    null,
    config
  );
}

export function syncUpstoxFundamentals(config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/sync-fundamentals",
    null,
    config
  );
}

export function syncUpstoxCorporateActions(config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/sync-corporate-actions",
    null,
    config
  );
}

export function syncUpstoxFiiDiiActivity(config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/sync-fii-dii-activity",
    null,
    config
  );
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
