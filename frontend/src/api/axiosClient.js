import axios from "axios";

function getDefaultApiBaseUrl() {
  const protocol = window.location.protocol === "https:" ? "https:" : "http:";
  const hostname = window.location.hostname || "127.0.0.1";

  return `${protocol}//${hostname}:8000/api/v1`;
}

const axiosClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || getDefaultApiBaseUrl(),
  headers: {
    "Content-Type": "application/json"
  }
});

function isAuthEndpoint(config) {
  const url = config?.url || "";

  return (
    url.includes("/auth/login") ||
    url.includes("/auth/me") ||
    url.includes("/users/me")
  );
}

function clearOpenAnalyticsSession() {
  localStorage.removeItem("open_analytics_token");
  localStorage.removeItem("open_analytics_user");
  localStorage.removeItem("open_analytics_current_user");
}

function redirectToLogin() {
  const currentPath = window.location.pathname;

  if (currentPath !== "/login") {
    window.location.replace("/login");
  }
}

function decodeJwtPayload(token) {
  try {
    const payload = token.split(".")[1];

    if (!payload) {
      return null;
    }

    const normalizedPayload = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decodedPayload = window.atob(normalizedPayload);

    return JSON.parse(decodedPayload);
  } catch {
    return null;
  }
}

function isTokenExpired(token) {
  const payload = decodeJwtPayload(token);

  if (!payload?.exp) {
    return false;
  }

  const expiryTime = payload.exp * 1000;

  return Date.now() >= expiryTime;
}

function isOpenAnalyticsAuthError(error) {
  const status = error.response?.status;
  const detail = error.response?.data?.detail;
  const config = error.config;

  if (status !== 401) {
    return false;
  }

  if (isAuthEndpoint(config)) {
    return true;
  }

  if (typeof detail === "string") {
    const cleanDetail = detail.toLowerCase();

    return (
      cleanDetail.includes("not authenticated") ||
      cleanDetail.includes("could not validate credentials") ||
      cleanDetail.includes("invalid authentication credentials") ||
      cleanDetail.includes("invalid authentication token") ||
      cleanDetail.includes("invalid or expired token") ||
      cleanDetail.includes("token has expired") ||
      cleanDetail.includes("user not found")
    );
  }

  return false;
}

axiosClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("open_analytics_token");

  if (token && isTokenExpired(token)) {
    clearOpenAnalyticsSession();
    redirectToLogin();

    return Promise.reject(new Error("Session expired"));
  }

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (isOpenAnalyticsAuthError(error)) {
      clearOpenAnalyticsSession();
      redirectToLogin();
    }

    return Promise.reject(error);
  }
);

export default axiosClient;
