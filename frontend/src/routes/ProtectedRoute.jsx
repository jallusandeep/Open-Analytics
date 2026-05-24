import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { getCurrentUser } from "../api/authApi";
import Spinner from "../components/common/Spinner";

function ProtectedRoute({ children }) {
  const [checking, setChecking] = useState(true);
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    async function verifyUserToken() {
      const token = localStorage.getItem("open_analytics_token");

      if (!token) {
        localStorage.removeItem("open_analytics_user");
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
      } catch {
        localStorage.removeItem("open_analytics_token");
        localStorage.removeItem("open_analytics_user");
        localStorage.removeItem("open_analytics_current_user");

        setAllowed(false);
      } finally {
        setChecking(false);
      }
    }

    verifyUserToken();
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
