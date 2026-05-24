import { useLocation, useNavigate } from "react-router-dom";
import {
  Brain,
  ChevronRight,
  Database,
  Home,
  LogOut,
  Search,
  Settings,
  Users
} from "lucide-react";

import Tooltip from "../common/Tooltip";

function MainLayout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();

  const savedUser =
    localStorage.getItem("open_analytics_current_user") ||
    localStorage.getItem("open_analytics_user");
  const user = savedUser ? JSON.parse(savedUser) : null;

  const isAdminUser = ["admin", "super_admin"].includes(user?.role);

  function handleLogout() {
    localStorage.removeItem("open_analytics_token");
    localStorage.removeItem("open_analytics_user");
    localStorage.removeItem("open_analytics_current_user");
    navigate("/login");
  }

  const menuItems = [
    {
      label: "Dashboard",
      icon: Home,
      path: "/dashboard",
      show: true,
      color: "text-sky-300",
      activeLine: "bg-sky-300"
    },
    {
      label: "Stocks",
      icon: Search,
      path: "/stocks",
      show: true,
      color: "text-emerald-300",
      activeLine: "bg-emerald-300"
    },
    {
      label: "Predictions",
      icon: Brain,
      path: "/predictions",
      show: true,
      color: "text-purple-300",
      activeLine: "bg-purple-300"
    },
    {
      label: "Database",
      icon: Database,
      path: "/database",
      show: true,
      color: "text-amber-300",
      activeLine: "bg-amber-300"
    },
    {
      label: "User Accounts",
      icon: Users,
      path: "/admin/users",
      show: isAdminUser,
      color: "text-indigo-300",
      activeLine: "bg-indigo-300"
    },
    {
      label: "Settings",
      icon: Settings,
      path: "/settings",
      show: true,
      color: "text-zinc-300",
      activeLine: "bg-zinc-300"
    }
  ];

  return (
    <div className="min-h-screen bg-oa-dark text-oa-text">
      <aside className="fixed left-0 top-0 z-40 flex h-screen w-14 flex-col border-r border-oa-border bg-black">
        <div className="flex h-9 items-center justify-center border-b border-oa-border">
          <Tooltip text="Open Analytics" side="right">
            <div className="flex h-8 w-8 items-center justify-center text-oa-text">
              <ChevronRight size={22} strokeWidth={2.5} />
            </div>
          </Tooltip>
        </div>

        <nav className="flex flex-1 flex-col items-center gap-1 px-2 py-2">
          {menuItems
            .filter((item) => item.show)
            .map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;

              return (
                <Tooltip key={item.label} text={item.label} side="right">
                  <button
                    onClick={() => navigate(item.path)}
                    className={`relative flex h-10 w-10 items-center justify-center rounded transition ${
                      isActive
                        ? "bg-oa-card"
                        : "hover:bg-oa-card"
                    }`}
                    aria-label={item.label}
                  >
                    {isActive && (
                      <span
                        className={`absolute left-0 h-5 w-[2px] rounded-r ${item.activeLine}`}
                      />
                    )}

                    <Icon
                      size={17}
                      className={`${item.color} ${
                        isActive ? "opacity-100" : "opacity-85"
                      }`}
                    />
                  </button>
                </Tooltip>
              );
            })}
        </nav>

        <div className="flex items-center justify-center border-t border-oa-border px-2 py-2">
          <Tooltip text="Logout" side="right">
            <button
              onClick={handleLogout}
              className="flex h-10 w-10 items-center justify-center rounded text-red-300 transition hover:bg-oa-card hover:text-red-200"
              aria-label="Logout"
            >
              <LogOut size={17} />
            </button>
          </Tooltip>
        </div>
      </aside>

      <main className="min-h-screen pl-14">{children}</main>
    </div>
  );
}

export default MainLayout;
