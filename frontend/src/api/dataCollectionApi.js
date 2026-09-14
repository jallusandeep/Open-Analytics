import axiosClient from "./axiosClient";

export function getUpstoxDataCollectionSummary() {
  return axiosClient.get("/data/upstox/summary");
}

export function getUpstoxDataCollectionRuns() {
  return axiosClient.get("/data/upstox/runs");
}

export function getUpstoxInstrumentsPreview(params = {}) {
  return axiosClient.get("/data/upstox/instruments", {
    params
  });
}

export function getUpstoxExpiredInstrumentsPreview(params = {}) {
  return axiosClient.get("/data/upstox/expired-instruments", {
    params
  });
}

export function getUpstoxOhlcvPreview(params = {}) {
  return axiosClient.get("/data/upstox/ohlcv/preview", {
    params
  });
}

export function getUpstoxMarketHolidaysPreview(params = {}) {
  return axiosClient.get("/data/upstox/calendar/preview", {
    params
  });
}

export function getUpstoxEquityNewsPreview(params = {}) {
  return axiosClient.get("/data/upstox/equity-news/preview", {
    params
  });
}

export function getUpstoxIpoCalendarPreview(params = {}) {
  return axiosClient.get("/data/upstox/ipo-calendar/preview", {
    params
  });
}
export function getIpoGmpScraperPreview(params = {}) {
  return axiosClient.get("/data/upstox/ipo-scraper/preview", {
    params
  });
}

export function getUpstoxOhlcvOptions() {
  return axiosClient.get("/data/upstox/ohlcv/options");
}

export function saveUpstoxOhlcvOptions(payload) {
  return axiosClient.put("/data/upstox/ohlcv/options", payload);
}

export function getUpstoxCompanyFundamentalsOptions() {
  return axiosClient.get(
    "/data/upstox/company-fundamentals/options"
  );
}

export function getUpstoxCompanyFundamentalsPreview(params = {}) {
  return axiosClient.get(
    "/data/upstox/company-fundamentals/preview",
    {
      params
    }
  );
}

export function syncUpstoxCompanyFundamentals(payload = {}, config = {}) {
  return axiosClient.post(
    "/data/upstox/company-fundamentals/run",
    payload,
    config
  );
}

export function syncUpstoxCurrentInstruments(config = {}) {
  return axiosClient.post("/data/upstox/sync-current", null, config);
}

export function syncUpstoxExpiredInstruments(payload = {}, config = {}) {
  return axiosClient.post(
    "/data/upstox/sync-expired",
    payload,
    config
  );
}

export function syncUpstoxOhlcvDaily(payload = {}, config = {}) {
  return axiosClient.post(
    "/data/upstox/ohlcv/run",
    payload,
    config
  );
}

export function syncUpstoxMarketHolidays(payload = {}, config = {}) {
  return axiosClient.post(
    "/data/upstox/calendar/run",
    payload,
    config
  );
}

export function syncUpstoxEquityNews(payload = {}, config = {}) {
  return axiosClient.post(
    "/data/upstox/equity-news/run",
    payload,
    config
  );
}

export function syncUpstoxIpoCalendar(payload = {}, config = {}) {
  return axiosClient.post(
    "/data/upstox/ipo-calendar/run",
    payload,
    config
  );
}

export function syncIpoGmpScraper(payload = {}, config = {}) {
  return axiosClient.post(
    "/data/upstox/ipo-scraper/run",
    payload,
    config
  );
}

export function cancelUpstoxDataCollection() {
  return axiosClient.post("/data/upstox/cancel");
}

export function getUpstoxDataCollectionSchedules() {
  return axiosClient.get("/data/upstox/schedules");
}

export function createUpstoxDataCollectionSchedule(payload) {
  return axiosClient.post("/data/upstox/schedules", payload);
}

export function updateUpstoxDataCollectionSchedule(scheduleId, payload) {
  return axiosClient.put(
    `/data/upstox/schedules/${scheduleId}`,
    payload
  );
}

export function toggleUpstoxDataCollectionSchedule(scheduleId) {
  return axiosClient.post(
    `/data/upstox/schedules/${scheduleId}/toggle`
  );
}

export function deleteUpstoxDataCollectionSchedule(scheduleId) {
  return axiosClient.delete(`/data/upstox/schedules/${scheduleId}`);
}