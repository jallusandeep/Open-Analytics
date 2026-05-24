import { BarChart3 } from "lucide-react";

import MainLayout from "../../components/layout/MainLayout";

function Dashboard() {
  return (
    <MainLayout title="Dashboard">
      <section className="p-3">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-oa-border bg-oa-card p-3">
            <p className="text-xs text-oa-muted">Total Stocks</p>
            <h3 className="mt-1 text-xl font-semibold">0</h3>
          </div>

          <div className="rounded-xl border border-oa-border bg-oa-card p-3">
            <p className="text-xs text-oa-muted">Predictions</p>
            <h3 className="mt-1 text-xl font-semibold">0</h3>
          </div>

          <div className="rounded-xl border border-oa-border bg-oa-card p-3">
            <p className="text-xs text-oa-muted">Accuracy</p>
            <h3 className="mt-1 text-xl font-semibold">--</h3>
          </div>

          <div className="rounded-xl border border-oa-border bg-oa-card p-3">
            <p className="text-xs text-oa-muted">Status</p>
            <h3 className="mt-1 text-xl font-semibold">Live</h3>
          </div>
        </div>

        <div className="mt-3 grid gap-3 xl:grid-cols-3">
          <div className="rounded-xl border border-oa-border bg-oa-card p-3 xl:col-span-2">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="text-xs text-oa-muted">Market View</p>
                <h3 className="text-base font-semibold">
                  Stock Analytics Overview
                </h3>
              </div>

              <BarChart3 size={18} className="text-oa-muted" />
            </div>

            <div className="flex h-[420px] items-center justify-center rounded-lg border border-dashed border-oa-border bg-black text-xs text-oa-muted">
              Chart area will come here
            </div>
          </div>

          <div className="rounded-xl border border-oa-border bg-oa-card p-3">
            <div className="mb-3">
              <p className="text-xs text-oa-muted">Recent Predictions</p>
              <h3 className="text-base font-semibold">No data yet</h3>
            </div>

            <div className="rounded-lg border border-oa-border bg-black p-3 oa-table-font">
              <div className="grid grid-cols-3 border-b border-oa-border pb-2 text-[10px] uppercase tracking-widest text-oa-muted">
                <span>#</span>
                <span>Code</span>
                <span>Alias</span>
              </div>

              {[
                ["01", "NSE", "nifty"],
                ["02", "BSE", "sensex"],
                ["03", "ML", "model"],
                ["04", "AI", "forecast"],
                ["05", "DB", "duckdb"]
              ].map((row) => (
                <div
                  key={row[0]}
                  className="grid grid-cols-3 border-b border-oa-border py-3 text-xs last:border-b-0"
                >
                  <span>{row[0]}</span>

                  <span>
                    <span className="rounded border border-oa-border bg-oa-panel px-1.5 py-0.5">
                      {row[1]}
                    </span>
                  </span>

                  <span className="font-semibold">{row[2]}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-3 rounded-xl border border-oa-border bg-oa-card p-3">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="text-xs text-oa-muted">Workspace</p>
              <h3 className="text-base font-semibold">Prediction Requests</h3>
            </div>

            <button className="h-8 rounded-lg bg-white px-3 text-xs font-semibold text-black transition hover:bg-zinc-200">
              New Prediction
            </button>
          </div>

          <div className="overflow-hidden rounded-lg border border-oa-border bg-black oa-table-font">
            <div className="grid grid-cols-5 border-b border-oa-border px-3 py-2 text-[10px] uppercase tracking-widest text-oa-muted">
              <span>#</span>
              <span>Symbol</span>
              <span>Model</span>
              <span>Status</span>
              <span>Created</span>
            </div>

            {[
              ["01", "RELIANCE", "LSTM", "pending", "--"],
              ["02", "TCS", "XGBOOST", "pending", "--"],
              ["03", "INFY", "ARIMA", "pending", "--"],
              ["04", "HDFC", "LSTM", "pending", "--"],
              ["05", "SBIN", "XGBOOST", "pending", "--"]
            ].map((row) => (
              <div
                key={row[0]}
                className="grid grid-cols-5 border-b border-oa-border px-3 py-2.5 text-xs last:border-b-0"
              >
                <span>{row[0]}</span>
                <span className="font-semibold">{row[1]}</span>
                <span>{row[2]}</span>
                <span>
                  <span className="rounded border border-oa-border bg-oa-panel px-2 py-0.5">
                    {row[3]}
                  </span>
                </span>
                <span>{row[4]}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </MainLayout>
  );
}

export default Dashboard;