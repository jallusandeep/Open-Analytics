import { referenceViews, referencePageUrl } from "../../utils/referenceNavigation";
import { dataPageUrl } from "../../utils/navigation";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Brain,
  BookOpen,
  ChevronRight,
  Database,
  Home,
  Link,
  LogOut,
  Search,
  Settings,
  Users
} from "lucide-react";

import axiosClient from "../../api/axiosClient";
import Tooltip from "../common/Tooltip";
import NavigationLink from "../common/NavigationLink";
import { getAppAccess } from "../../utils/appAccess";
import { clearSessionActivity } from "../../utils/sessionActivity";
import { viewOptions, ipoCalendarSubTabOptions, companyFundamentalsEndpointOptions } from "../../pages/admin/dataCollection/constants";

function MainLayout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [dataMenuOpen, setDataMenuOpen] = useState(false);
  const [dataPageMenuOpen, setDataPageMenuOpen] = useState(false);
  const [dataSubmenu, setDataSubmenu] = useState(null);
  const [dataMenuTop, setDataMenuTop] = useState(60);
  const [dataSubmenuTop, setDataSubmenuTop] = useState(60);
  const [referenceMenuOpen, setReferenceMenuOpen] = useState(false);
  const [referenceMenuTop, setReferenceMenuTop] = useState(60);
  const referenceMenuRef = useRef(null);
  const dataMenuRef = useRef(null);
  const dataSubmenuRef = useRef(null);

  useEffect(() => {
    function syncDataMenu(event) {
      setDataPageMenuOpen(Boolean(event.detail));
    }
    window.addEventListener("open-analytics:data-navigation-state", syncDataMenu);
    return () => window.removeEventListener("open-analytics:data-navigation-state", syncDataMenu);
  }, []);

  useEffect(() => {
    if (!dataMenuOpen) return undefined;
    function closeOutside(event) {
      if (document.querySelector('[aria-label="Data"]')?.contains(event.target)) return;
      if (!dataMenuRef.current?.contains(event.target) && !dataSubmenuRef.current?.contains(event.target)) {
        setDataMenuOpen(false);
        setDataSubmenu(null);
      }
    }
    function closeEscape(event) {
      if (event.key === "Escape") {
        setDataMenuOpen(false);
        setDataSubmenu(null);
      }
    }
    document.addEventListener("pointerdown", closeOutside, true);
    document.addEventListener("keydown", closeEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside, true);
      document.removeEventListener("keydown", closeEscape);
    };
  }, [dataMenuOpen]);

  useEffect(() => {
    function toggleReferenceMenu() {
      const top = document.querySelector('[aria-label="Reference Data"]')?.getBoundingClientRect().top ?? 60;
      setReferenceMenuTop(Math.max(8, Math.min(top, window.innerHeight - referenceViews.length * 36 - 16)));
      setReferenceMenuOpen((current) => !current);
      setDataMenuOpen(false);
      setDataSubmenu(null);
      if (dataPageMenuOpen) window.dispatchEvent(new Event("open-analytics:data-navigation-toggle"));
    }
    window.addEventListener("open-analytics:reference-navigation-toggle", toggleReferenceMenu);
    return () => window.removeEventListener("open-analytics:reference-navigation-toggle", toggleReferenceMenu);
  }, [dataPageMenuOpen]);

  useEffect(() => {
    if (!referenceMenuOpen) return;
    function closeOutside(event) {
      if (document.querySelector('[aria-label="Reference Data"]')?.contains(event.target)) return;
      if (event.target.closest('[aria-label="Reference Data breadcrumb"]')) return;
      if (!referenceMenuRef.current?.contains(event.target)) setReferenceMenuOpen(false);
    }
    function closeEscape(event) { if (event.key === "Escape") setReferenceMenuOpen(false); }
    document.addEventListener("pointerdown", closeOutside, true);
    document.addEventListener("keydown", closeEscape);
    return () => { document.removeEventListener("pointerdown", closeOutside, true); document.removeEventListener("keydown", closeEscape); };
  }, [referenceMenuOpen]);

  function openDataPage(view, subpage) {
    sessionStorage.setItem("open_analytics_data_target", JSON.stringify({ view, subpage }));
    setDataMenuOpen(false);
    setDataSubmenu(null);
    navigate(dataPageUrl(view, subpage));
  }

  const savedUser =
    sessionStorage.getItem("open_analytics_current_user") ||
    sessionStorage.getItem("open_analytics_user");

  const user = savedUser ? JSON.parse(savedUser) : null;
  const isAdminUser = ["admin", "super_admin"].includes(user?.role);
  const appAccess = getAppAccess(user);
  const isAdminApp = isAdminUser && (location.pathname === "/data" || location.pathname === "/reference-data" || location.pathname.startsWith("/connections") || location.pathname.startsWith("/admin/"));

  function clearOpenAnalyticsSession() {
    sessionStorage.removeItem("open_analytics_token");
    sessionStorage.removeItem("open_analytics_user");
    sessionStorage.removeItem("open_analytics_current_user");
    clearSessionActivity();
  }

  async function handleLogout() {
    try {
      await axiosClient.post("/auth/logout");
    } catch {
      // Still clear local session even if backend logout fails.
    } finally {
      clearOpenAnalyticsSession();
      navigate("/login");
    }
  }

  const menuItems = [
    {
      label: "Dashboard",
      icon: Home,
      path: "/dashboard",
      show: !isAdminApp && appAccess.includes("trading"),
      color: "text-sky-300",
      activeLine: "bg-sky-300"
    },
    {
      label: "Stocks",
      icon: Search,
      path: "/stocks",
      show: !isAdminApp && appAccess.includes("trading"),
      color: "text-emerald-300",
      activeLine: "bg-emerald-300"
    },
    {
      label: "Predictions",
      icon: Brain,
      path: "/predictions",
      show: !isAdminApp && appAccess.includes("recom"),
      color: "text-purple-300",
      activeLine: "bg-purple-300"
    },
    {
      label: "Connections",
      icon: Link,
      path: "/connections",
      show: isAdminApp,
      color: "text-teal-300",
      activeLine: "bg-teal-300"
    },
    {
      label: "Data",
      icon: Database,
      path: "/data",
      show: isAdminApp,
      color: "text-amber-300",
      activeLine: "bg-amber-300"
    },
    {
      label: "Reference Data",
      icon: BookOpen,
      path: "/reference-data",
      show: isAdminApp,
      color: "text-cyan-300",
      activeLine: "bg-cyan-300"
    },
    {
      label: "User Accounts",
      icon: Users,
      path: "/admin/users",
      show: isAdminApp,
      color: "text-indigo-300",
      activeLine: "bg-indigo-300"
    },
    {
      label: "Settings",
      icon: Settings,
      path: "/settings",
      show: !isAdminApp,
      color: "text-zinc-300",
      activeLine: "bg-zinc-300"
    }
  ];

  return (
    <div className="min-h-screen bg-oa-dark text-oa-text">
      <aside className="fixed left-0 top-0 z-40 flex h-screen w-14 flex-col border-r border-oa-border bg-black">
        <div className="flex h-12 shrink-0 items-center justify-center border-b border-oa-border">
          <Tooltip text="Switch app" side="right" fixedSide>
            <NavigationLink to="/apps" aria-label="Switch app" onClick={() => navigate("/apps")} className="flex h-10 w-10 items-center justify-center rounded text-oa-text transition hover:bg-oa-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">
              <ChevronRight size={22} strokeWidth={2.5} />
            </NavigationLink>
          </Tooltip>
        </div>

        <nav className="flex flex-1 flex-col items-center gap-1 px-2 py-2">
          {menuItems
            .filter((item) => item.show)
            .map((item) => {
              const Icon = item.icon;
              const dataListOpen = item.path === "/data" && (dataMenuOpen || dataPageMenuOpen);
              const listOpen = dataListOpen || (item.path === "/reference-data" && referenceMenuOpen);
              const isActive = location.pathname === item.path || listOpen;

              return (
                <Tooltip key={`${item.label}-${listOpen}`} text={listOpen ? "" : item.label} side="right" fixedSide>
                  <NavigationLink to={item.path}
                    onClick={(event) => {
                      if (item.path === "/data") {
                        setReferenceMenuOpen(false);
                        if (location.pathname === "/data") {
                          window.dispatchEvent(new Event("open-analytics:data-navigation-toggle"));
                        } else {
                          setDataMenuTop(event.currentTarget.getBoundingClientRect().top);
                          setDataSubmenu(null);
                          setDataMenuOpen((current) => !current);
                        }
                      } else if (item.path === "/reference-data") {
                        setDataMenuOpen(false); setDataSubmenu(null);
                        if (dataPageMenuOpen) window.dispatchEvent(new Event("open-analytics:data-navigation-toggle"));
                        setReferenceMenuTop(Math.max(8, Math.min(event.currentTarget.getBoundingClientRect().top, window.innerHeight - referenceViews.length * 36 - 16)));
                        setReferenceMenuOpen((current) => !current);
                      } else {
                        setReferenceMenuOpen(false);
                        navigate(item.path);
                      }
                    }}
                    className={`relative flex h-10 w-10 items-center justify-center rounded transition ${
                      isActive ? "bg-oa-card" : "hover:bg-oa-card"
                    }`}
                    aria-label={item.label}
                  >
                    {isActive && (!listOpen || location.pathname === item.path) && (
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
                  </NavigationLink>
                </Tooltip>
              );
            })}
        </nav>

        <div className="flex items-center justify-center border-t border-oa-border px-2 py-2">
          <Tooltip text="Logout" side="right" fixedSide>
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

      {referenceMenuOpen && createPortal(<nav ref={referenceMenuRef} aria-label="Reference Data tables" style={{ top: referenceMenuTop }} className="fixed left-14 z-[20000] max-h-[calc(100vh-16px)] w-64 origin-top overflow-y-auto rounded-r border border-oa-border bg-[#101010] p-1 shadow-2xl animate-[oaSelectDown_0.1s_ease-out]">
        {referenceViews.map((view) => {
          const selected = location.pathname === "/reference-data" && (new URLSearchParams(location.search).get("view") || "securities") === view.value;
          return <NavigationLink key={view.value} to={referencePageUrl(view.value)} onClick={() => { setReferenceMenuOpen(false); navigate(referencePageUrl(view.value)); }} aria-current={selected ? "page" : undefined} className={`flex w-full items-center justify-between rounded px-3 py-2 text-left font-mono text-xs hover:bg-[#2b2b2b] hover:text-sky-300 ${selected ? "bg-[#2b2b2b] text-sky-300" : "text-oa-muted"}`}>
            {view.label}
          </NavigationLink>;
        })}
      </nav>, document.body)}
      {dataMenuOpen && createPortal(<nav ref={dataMenuRef} aria-label="Data pages" style={{ top: dataMenuTop }} className="fixed left-14 z-[20000] max-h-[calc(100vh-16px)] w-64 origin-top overflow-y-auto rounded-r border border-oa-border bg-[#101010] p-1 shadow-2xl animate-[oaSelectDown_0.1s_ease-out]">
        {viewOptions.map((view) => {
          const subpages = view.key === "ipo_calendar" ? ipoCalendarSubTabOptions : view.key === "company_fundamentals" ? companyFundamentalsEndpointOptions : [];
          return <NavigationLink to={dataPageUrl(view.key)} key={view.key} onMouseEnter={(event) => {
            if (!subpages.length) {
              setDataSubmenu(null);
              return;
            }
            setDataSubmenuTop(Math.max(8, Math.min(event.currentTarget.getBoundingClientRect().top, window.innerHeight - subpages.length * 30 - 16)));
            setDataSubmenu(view.key);
          }} onClick={(event) => {
            if (!subpages.length) return openDataPage(view.key);
            setDataSubmenuTop(Math.max(8, Math.min(event.currentTarget.getBoundingClientRect().top, window.innerHeight - subpages.length * 30 - 16)));
            setDataSubmenu(view.key);
          }} aria-expanded={subpages.length ? dataSubmenu === view.key : undefined} className={`flex w-full items-center justify-between rounded px-3 py-2 text-left font-mono text-xs hover:bg-[#2b2b2b] hover:text-sky-300 ${dataSubmenu === view.key ? "bg-[#2b2b2b] text-sky-300" : "text-oa-muted"}`}>
            {view.label}{subpages.length ? <ChevronRight size={13} className={dataSubmenu === view.key ? "text-sky-400" : ""} /> : null}
          </NavigationLink>;
        })}
      </nav>, document.body)}
      {dataMenuOpen && dataSubmenu && createPortal(<nav ref={dataSubmenuRef} aria-label="Data subpages" style={{ top: dataSubmenuTop }} className="fixed left-[312px] z-[20001] max-h-[calc(100vh-16px)] w-56 origin-top overflow-y-auto rounded-r border border-oa-border bg-[#101010] p-1 shadow-2xl animate-[oaSelectDown_0.1s_ease-out]">
        {(dataSubmenu === "ipo_calendar" ? ipoCalendarSubTabOptions : companyFundamentalsEndpointOptions).map((subpage) => <NavigationLink to={dataPageUrl(dataSubmenu, subpage.value)} key={subpage.value} onClick={() => openDataPage(dataSubmenu, subpage.value)} className="block w-full rounded px-3 py-1.5 text-left font-mono text-[11px] text-oa-muted hover:bg-white/10 hover:text-white">{subpage.label}</NavigationLink>)}
      </nav>, document.body)}

      <main className="min-h-screen pl-14">{children}</main>
    </div>
  );
}

export default MainLayout;
