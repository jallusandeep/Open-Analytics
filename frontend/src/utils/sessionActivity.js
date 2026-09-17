export const SESSION_IDLE_MS = 8 * 60 * 60 * 1000;
const LAST_ACTIVITY_KEY = "open_analytics_last_activity";

export function recordSessionActivity(now = Date.now()) {
  sessionStorage.setItem(LAST_ACTIVITY_KEY, String(now));
}

export function isSessionIdle(now = Date.now()) {
  const lastActivity = Number(sessionStorage.getItem(LAST_ACTIVITY_KEY));
  return !lastActivity || now - lastActivity >= SESSION_IDLE_MS;
}

export function getSessionIdleDeadline() {
  return Number(sessionStorage.getItem(LAST_ACTIVITY_KEY)) + SESSION_IDLE_MS;
}

export function clearSessionActivity() {
  sessionStorage.removeItem(LAST_ACTIVITY_KEY);
}
