import { ChartCandlestick, ChevronRight, ShieldCheck, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getAppAccess } from "../../utils/appAccess";
import { useState } from "react";
import NavigationLink from "../../components/common/NavigationLink";


const apps = [
  { name: "Trading", icon: ChartCandlestick, path: "/dashboard", description: "Markets & trading" },
  { name: "Admin", icon: ShieldCheck, path: "/connections", description: "Data & administration", admin: true },
  { name: "Recon", accessKey: "recom", icon: Sparkles, description: "Under development" }
];

export default function AppSelector() {
  const navigate = useNavigate();
  const user = JSON.parse(sessionStorage.getItem("open_analytics_current_user") || "null");
  const [notice, setNotice] = useState("");
  const access = getAppAccess(user);

  return (
    <div className="oa-app-font flex min-h-screen flex-col bg-black text-white">
      <header className="flex items-center gap-2 px-6 py-7 sm:px-12">
        <ChevronRight size={26} strokeWidth={2.5} />
        <span className="text-lg font-semibold tracking-wide">Open Analytics</span>
      </header>
      <main className="flex flex-1 flex-col items-center justify-center px-6 pb-24 pt-8 sm:pb-48">
        <div aria-label="Choose your app" className="flex flex-wrap justify-center gap-7 sm:gap-10">
          {apps.filter((app) => access.includes(app.accessKey || app.name.toLowerCase())).map(({ name, icon: Icon, path, description }) => {
            const AppControl = path ? NavigationLink : "button";
            return (
              <AppControl to={path}
                key={name}
                onClick={() => {
                  if (name === "Recon") {
                    setNotice("Recon is still under development.");
                    return;
                  }
                  setNotice("");
                  sessionStorage.setItem("open_analytics_selected_app", name.toLowerCase());
                  navigate(path);
                }}
                className="group w-44 rounded text-center outline-none sm:w-48 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label={name === "Recon" ? "Recon is under development" : `Open ${name}`}
              >
                <div className="relative flex aspect-square flex-col items-center justify-center rounded border border-zinc-800 bg-[#101010] px-3 text-zinc-300 transition-all duration-300 ease-out group-hover:-translate-y-1 group-hover:border-white/70 group-hover:bg-[#191919] group-hover:text-white group-focus-visible:ring-2 group-focus-visible:ring-white group-focus-visible:ring-offset-4 group-focus-visible:ring-offset-black motion-reduce:transition-none motion-reduce:group-hover:translate-y-0">
                  <Icon size={48} strokeWidth={1.3} className="transition-transform duration-300 group-hover:scale-105 motion-reduce:transition-none" />
                  <h2 className="mt-4 text-sm font-semibold text-zinc-300 transition-colors group-hover:text-white">{name}</h2>
                  <p className="mt-2 text-[11px] leading-4 text-zinc-500">{description}</p>
                </div>
              </AppControl>
            );
          })}
        </div>
        {notice && <p role="status" className="mt-6 text-sm text-zinc-400">{notice}</p>}
        {!access.length ? <p className="text-sm text-zinc-400">No apps are enabled. Contact your administrator.</p> : null}
      </main>
    </div>
  );
}
