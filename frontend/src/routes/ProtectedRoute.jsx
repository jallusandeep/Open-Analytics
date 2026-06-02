import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { getCurrentUser } from "../api/authApi";
import Spinner from "../components/common/Spinner";

function clearOpenAnalyticsSession() {
  localStorage.removeItem("open_analytics_token");
  localStorage.removeItem("open_analytics_user");
  localStorage.removeItem("open_analytics_current_user");
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
  const [checking, setChecking] = useState(true);
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let logoutTimer = null;

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

      if (isTokenExpired(token)) {
        clearOpenAnalyticsSession();
        setAllowed(false);
        setChecking(false);
        return;
      }

      try {
        const response = await getCurrentUser();
        const currentUser = response.data.user || response.data;

        localStorage.setItem(
          "open_analytics_current_user",
          JSON.stringify(currentUser)
        );

        setAllowed(true);
        startAutoLogoutTimer(token);
      } catch {
        clearOpenAnalyticsSession();
        setAllowed(false);
      } finally {
        setChecking(false);
      }
    }

    verifyUserToken();

    return () => {
      if (logoutTimer) {
        window.clearTimeout(logoutTimer);
      }
    };
  }, []);

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-oa-dark text-oa-text">
        <div className="flex items-center gap-2 rounded-lg border border-oa-border bg-oa-card px-4 py-3 text-sm text-oa-muted">
          <Spinner size="sm" color="light" />
          Checking login
        </div>
      </div>
    );
  }

  if (!allowed) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default ProtectedRoute;