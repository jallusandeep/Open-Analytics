import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getAppAccess } from "../utils/appAccess";

import { getCurrentUser } from "../api/authApi";
import ScreenLoading from "../components/common/ScreenLoading";
import { clearSessionActivity, getSessionIdleDeadline, isSessionIdle, recordSessionActivity } from "../utils/sessionActivity";

function clearOpenAnalyticsSession() {
  localStorage.removeItem("open_analytics_token");
  localStorage.removeItem("open_analytics_user");
  localStorage.removeItem("open_analytics_current_user");
  clearSessionActivity();
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

function getTokenExpiryTime(token) {
  const payload = decodeJwtPayload(token);

  if (!payload?.exp) {
    return null;
  }

  return payload.exp * 1000;
}

function isTokenExpired(token) {
  const expiryTime = getTokenExpiryTime(token);

  if (!expiryTime) {
    return false;
  }

  return Date.now() >= expiryTime;
}

function ProtectedRoute({ children }) {
  const location = useLocation();
  const [checking, setChecking] = useState(true);
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let logoutTimer = null;
    let idleCheckTimer = null;
    let heartbeatTimer = null;
    let lastRecordedActivity = 0;
    let disposed = false;

    function handleActivity() {
      const now = Date.now();
      if (now - lastRecordedActivity < 30000 || isSessionIdle(now)) return;
      lastRecordedActivity = now;
      recordSessionActivity(now);
    }

    function logoutUser() {
      clearOpenAnalyticsSession();
      setAllowed(false);
      setChecking(false);
    }

    function startAutoLogoutTimer(token) {
      const expiryTime = getTokenExpiryTime(token);

      if (!expiryTime) {
        return;
      }

      const timeUntilExpiry = expiryTime - Date.now();

      if (timeUntilExpiry <= 0) {
        logoutUser();
        return;
      }

      logoutTimer = window.setTimeout(() => {
        logoutUser();
      }, timeUntilExpiry);
    }

    async function verifyUserToken() {
      const token = localStorage.getItem("open_analytics_token");

      if (!token) {
        clearOpenAnalyticsSession();
        setAllowed(false);
        setChecking(false);
        return;
      }

      if (isTokenExpired(token) || isSessionIdle()) {
        clearOpenAnalyticsSession();
        setAllowed(false);
        setChecking(false);
        return;
      }

      try {
        const response = await getCurrentUser();
        if (disposed) return;
        const currentUser = response.data.user || response.data;

        localStorage.setItem(
          "open_analytics_current_user",
          JSON.stringify(currentUser)
        );

        setAllowed(true);
        startAutoLogoutTimer(token);
        for (const eventName of ["pointerdown", "pointermove", "keydown", "wheel", "touchstart"]) {
          window.addEventListener(eventName, handleActivity, { passive: true });
        }
        idleCheckTimer = window.setInterval(() => {
          if (Date.now() >= getSessionIdleDeadline() || isTokenExpired(token)) logoutUser();
        }, 30000);
        heartbeatTimer = window.setInterval(async () => {
          if (isSessionIdle()) {
            logoutUser();
            return;
          }
          try {
            await getCurrentUser();
          } catch {
            logoutUser();
          }
        }, 60 * 1000);
      } catch {
        if (disposed) return;
        clearOpenAnalyticsSession();
        setAllowed(false);
      } finally {
        if (!disposed) setChecking(false);
      }
    }

    verifyUserToken();

    return () => {
      disposed = true;
      if (logoutTimer) {
        window.clearTimeout(logoutTimer);
      }
      if (idleCheckTimer) window.clearInterval(idleCheckTimer);
      if (heartbeatTimer) window.clearInterval(heartbeatTimer);
      for (const eventName of ["pointerdown", "pointermove", "keydown", "wheel", "touchstart"]) {
        window.removeEventListener(eventName, handleActivity);
      }
    };
  }, []);

  if (checking) {
    return <ScreenLoading message="Authenticating" />;
  }

  if (!allowed) {
    return <Navigate to="/login" replace />;
  }

  const user = JSON.parse(localStorage.getItem("open_analytics_current_user") || "null");
  const path = location.pathname;
  const app = path === "/data" || path.startsWith("/admin/") || path.startsWith("/connections") ? "admin" : path === "/predictions" ? "recom" : path === "/dashboard" || path.startsWith("/stocks") ? "trading" : null;
  if (app && !getAppAccess(user).includes(app)) return <Navigate to="/apps" replace />;
  return children;
}

export default ProtectedRoute;
