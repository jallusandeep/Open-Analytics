import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getAppAccess } from "../utils/appAccess";

import { getCurrentUser } from "../api/authApi";
import ScreenLoading from "../components/common/ScreenLoading";
import { clearSessionActivity, getSessionIdleDeadline, isSessionIdle, recordSessionActivity } from "../utils/sessionActivity";

function clearOpenAnalyticsSession() {
  sessionStorage.removeItem("open_analytics_token");
  sessionStorage.removeItem("open_analytics_user");
  sessionStorage.removeItem("open_analytics_current_user");
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

let authenticatedToken = null;

function ProtectedRoute({ children }) {
  const location = useLocation();
  const [checking, setChecking] = useState(() => !authenticatedToken || authenticatedToken !== sessionStorage.getItem("open_analytics_token"));
  const [allowed, setAllowed] = useState(() => Boolean(authenticatedToken && authenticatedToken === sessionStorage.getItem("open_analytics_token")));

  useEffect(() => {
    let disposed = false;
    let verifying = false;
    let lastRecordedActivity = 0;
    let expiryTimer = null;
    const token = sessionStorage.getItem("open_analytics_token");

    function logoutUser() {
      if (disposed) return;
      authenticatedToken = null;
      clearOpenAnalyticsSession();
      setAllowed(false);
      setChecking(false);

    }

    function handleActivity() {
      const now = Date.now();
      if (now - lastRecordedActivity < 30000 || isSessionIdle(now)) return;
      lastRecordedActivity = now;
      recordSessionActivity(now);
    }

    async function verifyUserToken() {
      if (disposed || verifying) return;
      if (!token || sessionStorage.getItem("open_analytics_token") !== token || isTokenExpired(token) || isSessionIdle()) {
        logoutUser();
        return;
      }
      if (authenticatedToken === token) {
        setAllowed(true);
        setChecking(false);
        return;
      }
      verifying = true;
      setChecking(true);
      try {
        const response = await getCurrentUser();
        if (disposed) return;
        if (sessionStorage.getItem("open_analytics_token") !== token) {
          logoutUser();
          return;
        }
        const currentUser = response.data.user || response.data;
        sessionStorage.setItem("open_analytics_current_user", JSON.stringify(currentUser));
        authenticatedToken = token;
        setAllowed(true);

      } catch {
        logoutUser();
      } finally {
        verifying = false;
        if (!disposed) setChecking(false);
      }
    }

    verifyUserToken();
    const expiryTime = token && getTokenExpiryTime(token);
    if (expiryTime) expiryTimer = window.setTimeout(logoutUser, Math.max(0, expiryTime - Date.now()));
    const idleTimer = window.setInterval(() => {
      if (Date.now() >= getSessionIdleDeadline() || token && isTokenExpired(token)) logoutUser();
    }, 30000);
    const activityEvents = ["pointerdown", "pointermove", "keydown", "wheel", "touchstart"];
    activityEvents.forEach((name) => window.addEventListener(name, handleActivity, { passive: true }));
    return () => {
      disposed = true;
      window.clearTimeout(expiryTimer);
      window.clearInterval(idleTimer);
      activityEvents.forEach((name) => window.removeEventListener(name, handleActivity));
    };
  }, []);

  if (checking) {
    return <ScreenLoading message="Authenticating" />;
  }
  if (!allowed) return <Navigate to="/login" replace />;

  const user = JSON.parse(sessionStorage.getItem("open_analytics_current_user") || "null");
  const path = location.pathname;
  const app = path === "/data" || path === "/reference-data" || path.startsWith("/admin/") || path.startsWith("/connections") ? "admin" : path === "/predictions" ? "recom" : path === "/dashboard" || path.startsWith("/stocks") ? "trading" : null;
  if (app && !getAppAccess(user).includes(app)) return <Navigate to="/apps" replace />;
  return children;
}

export default ProtectedRoute;
