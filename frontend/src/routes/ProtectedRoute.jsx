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

function ProtectedRoute({ children }) {
  const location = useLocation();
  const [checking, setChecking] = useState(true);
  const [allowed, setAllowed] = useState(false);
  const [verifiedPath, setVerifiedPath] = useState(null);

  useEffect(() => {
    let disposed = false;
    let verifying = false;
    let lastRecordedActivity = 0;
    let expiryTimer = null;
    const token = sessionStorage.getItem("open_analytics_token");

    function logoutUser() {
      if (disposed) return;
      clearOpenAnalyticsSession();
      setAllowed(false);
      setChecking(false);
      setVerifiedPath(location.pathname);
    }

    function handleActivity() {
      const now = Date.now();
      if (now - lastRecordedActivity < 30000 || isSessionIdle(now)) return;
      lastRecordedActivity = now;
      recordSessionActivity(now);
    }

    async function verifyUserToken(showLoader = true) {
      if (disposed || verifying) return;
      if (!token || sessionStorage.getItem("open_analytics_token") !== token || isTokenExpired(token) || isSessionIdle()) {
        logoutUser();
        return;
      }
      verifying = true;
      if (showLoader) setChecking(true);
      try {
        const response = await getCurrentUser();
        if (disposed) return;
        if (sessionStorage.getItem("open_analytics_token") !== token) {
          logoutUser();
          return;
        }
        const currentUser = response.data.user || response.data;
        sessionStorage.setItem("open_analytics_current_user", JSON.stringify(currentUser));
        setAllowed(true);
        setVerifiedPath(location.pathname);
      } catch {
        logoutUser();
      } finally {
        verifying = false;
        if (!disposed) setChecking(false);
      }
    }

    function handleReturn() {
      if (document.visibilityState === "visible") verifyUserToken();
    }

    verifyUserToken();
    const expiryTime = token && getTokenExpiryTime(token);
    if (expiryTime) expiryTimer = window.setTimeout(logoutUser, Math.max(0, expiryTime - Date.now()));
    const idleTimer = window.setInterval(() => {
      if (Date.now() >= getSessionIdleDeadline() || token && isTokenExpired(token)) logoutUser();
    }, 30000);
    const heartbeatTimer = window.setInterval(() => {
      if (document.visibilityState === "visible") verifyUserToken(false);
    }, 60000);
    const activityEvents = ["pointerdown", "pointermove", "keydown", "wheel", "touchstart"];
    activityEvents.forEach((name) => window.addEventListener(name, handleActivity, { passive: true }));
    window.addEventListener("focus", handleReturn);
    document.addEventListener("visibilitychange", handleReturn);
    return () => {
      disposed = true;
      window.clearTimeout(expiryTimer);
      window.clearInterval(idleTimer);
      window.clearInterval(heartbeatTimer);
      activityEvents.forEach((name) => window.removeEventListener(name, handleActivity));
      window.removeEventListener("focus", handleReturn);
      document.removeEventListener("visibilitychange", handleReturn);
    };
  }, [location.pathname]);

  if (checking || verifiedPath !== location.pathname) {
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
