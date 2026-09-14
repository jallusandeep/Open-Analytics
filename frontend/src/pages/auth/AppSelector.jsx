import { ArrowUpRight, ChartCandlestick, ChevronRight, ShieldCheck, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

const apps = [
  { name: "Trading", icon: ChartCandlestick, path: "/dashboard", description: "Markets & trading" },
  { name: "Admin", icon: ShieldCheck, path: "/data", description: "Data & administration", admin: true },
  { name: "Recom", icon: Sparkles, path: "/predictions", description: "Research & recommendations" }
];

export default function AppSelector() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("open_analytics_current_user") || "null");
  const isAdmin = ["admin", "super_admin"].includes(user?.role);

  return (
    <div className="oa-app-font flex min-h-screen flex-col bg-black text-white">
      <header className="flex items-center gap-2 px-6 py-7 sm:px-12">
        <ChevronRight size={26} strokeWidth={2.5} />
        <span className="text-lg font-semibold tracking-wide">Open Analytics</span>
      </header>
      <main className="flex flex-1 flex-col items-center justify-center px-6 pb-24 pt-8 sm:pb-48">
        <p className="mb-4 text-[11px] uppercase tracking-[0.18em] text-zinc-500">Your workspace</p>
        <h1 className="text-center text-2xl font-medium tracking-tight sm:text-3xl">Choose your app</h1>
        <p className="mt-4 text-center text-sm text-zinc-400">Choose an app to get started.</p>
        <div className="mt-12 flex flex-wrap justify-center gap-7 sm:gap-10">
          {apps.filter((app) => !app.admin || isAdmin).map(({ name, icon: Icon, path, description }) => {
            return (
              <button
                key={name}
                type="button"
                onClick={() => {
                  sessionStorage.setItem("open_analytics_selected_app", name.toLowerCase());
                  navigate(path);
                }}
                className="group w-44 rounded-2xl text-center outline-none sm:w-48 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label={`Open ${name}`}
              >
                <div className="relative flex aspect-square flex-col items-center justify-center rounded-xl border border-zinc-800 bg-[#101010] px-3 text-zinc-300 transition-all duration-300 ease-out group-hover:-translate-y-1 group-hover:border-white/70 group-hover:bg-[#191919] group-hover:text-white group-focus-visible:ring-2 group-focus-visible:ring-white group-focus-visible:ring-offset-4 group-focus-visible:ring-offset-black motion-reduce:transition-none motion-reduce:group-hover:translate-y-0">
                  <Icon size={48} strokeWidth={1.3} className="transition-transform duration-300 group-hover:scale-105 motion-reduce:transition-none" />
                  <ArrowUpRight size={15} className="absolute right-4 top-4 text-zinc-600 transition-colors group-hover:text-white" />
                  <h2 className="mt-4 text-sm font-semibold text-zinc-300 transition-colors group-hover:text-white">{name}</h2>
                  <p className="mt-2 text-[11px] leading-4 text-zinc-500">{description}</p>
                </div>
              </button>
            );
          })}
        </div>
      </main>
    </div>
  );
}
