import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Login from "./pages/auth/Login";
import Dashboard from "./pages/dashboard/Dashboard";
import UserAccounts from "./pages/admin/UserAccounts";
import Connections from "./pages/admin/Connections";
import UpstoxCallback from "./pages/admin/UpstoxCallback";
import DataCollection from "./pages/admin/DataCollection";
import Settings from "./pages/settings/Settings";

import ProtectedRoute from "./routes/ProtectedRoute";
import AdminRoute from "./routes/AdminRoute";
import { ToastProvider } from "./components/common/ToastProvider";

function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          <Route path="/login" element={<Login />} />

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            }
          />

          <Route
            path="/connections"
            element={
              <ProtectedRoute>
                <AdminRoute>
                  <Connections />
                </AdminRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/connections/upstox/callback"
            element={
              <ProtectedRoute>
                <AdminRoute>
                  <UpstoxCallback />
                </AdminRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/data-collection"
            element={
              <ProtectedRoute>
                <AdminRoute>
                  <DataCollection />
                </AdminRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/users"
            element={
              <ProtectedRoute>
                <AdminRoute>
                  <UserAccounts />
                </AdminRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/data-collection"
            element={<Navigate to="/admin/data-collection" replace />}
          />

          <Route
            path="/user-accounts"
            element={<Navigate to="/admin/users" replace />}
          />

          <Route
            path="/users"
            element={<Navigate to="/admin/users" replace />}
          />

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
}

export default App;