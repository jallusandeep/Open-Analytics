import { Navigate } from "react-router-dom";

function AdminRoute({ children }) {
  const savedUser = localStorage.getItem("open_analytics_current_user");
  const user = savedUser ? JSON.parse(savedUser) : null;

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!["admin", "super_admin"].includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

export default AdminRoute;