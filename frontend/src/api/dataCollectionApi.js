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

export function getUpstoxMarketHolidaysPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/calendar/preview", {
    params
  });
}

export function getUpstoxEquityNewsPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/equity-news/preview", {
    params
  });
}

export function getUpstoxIpoCalendarPreview(params = {}) {
  return axiosClient.get("/data-collection/upstox/ipo-calendar/preview", {
    params
  });
}

export function getUpstoxOhlcvOptions() {
  return axiosClient.get("/data-collection/upstox/ohlcv/options");
}

export function saveUpstoxOhlcvOptions(payload) {
  return axiosClient.put("/data-collection/upstox/ohlcv/options", payload);
}

export function getUpstoxCompanyFundamentalsOptions() {
  return axiosClient.get(
    "/data-collection/upstox/company-fundamentals/options"
  );
}

export function getUpstoxCompanyFundamentalsPreview(params = {}) {
  return axiosClient.get(
    "/data-collection/upstox/company-fundamentals/preview",
    {
      params
    }
  );
}

export function syncUpstoxCompanyFundamentals(payload = {}, config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/company-fundamentals/run",
    payload,
    config
  );
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

export function syncUpstoxMarketHolidays(payload = {}, config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/calendar/run",
    payload,
    config
  );
}

export function syncUpstoxEquityNews(payload = {}, config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/equity-news/run",
    payload,
    config
  );
}

export function syncUpstoxIpoCalendar(payload = {}, config = {}) {
  return axiosClient.post(
    "/data-collection/upstox/ipo-calendar/run",
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