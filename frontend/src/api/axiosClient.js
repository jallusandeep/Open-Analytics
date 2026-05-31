import axios from "axios";

const axiosClient = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
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

  if (status !== 401 && status !== 403) {
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
      cleanDetail.includes("token has expired") ||
      cleanDetail.includes("not enough permissions")
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