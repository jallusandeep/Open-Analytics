import { useEffect, useState } from "react";

import { getAutomatedStockPredictions } from "../../api/quantResearchApi";
import Spinner from "../../components/common/Spinner";
import MainLayout from "../../components/layout/MainLayout";

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "-";
  }

  return number.toFixed(digits);
}

function formatPrice(value) {
  return formatNumber(value, 2);
}

function getRecommendationClass(recommendation) {
  if (recommendation === "BUY") {
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
  }

  if (recommendation === "SELL") {
    return "border-red-500/40 bg-red-500/10 text-red-200";
  }

  return "border-amber-500/40 bg-amber-500/10 text-amber-200";
}

export default function QuantResearch() {
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadPredictions() {
      setLoading(true);
      setError("");

      try {
        const response = await getAutomatedStockPredictions();
        const data = response.data?.data || {};

        if (!active) {
          return;
        }

        setRows(Array.isArray(data.rows) ? data.rows : []);
        setMeta(data);
      } catch (err) {
        if (!active) {
          return;
        }

        setError(err?.response?.data?.detail || err?.message || "Unable to load predictions.");
        setRows([]);
        setMeta(null);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadPredictions();

    return () => {
      active = false;
    };
  }, []);

  return (
    <MainLayout>
      <div className="space-y-4 px-4 py-4 lg:px-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold text-white">Predictions</h1>
            <p className="mt-1 text-sm text-oa-muted">
              Automated OHLCV based equity predictions with buy, hold, and sell recommendations.
            </p>
          </div>

          <div className="text-right text-xs text-oa-muted">
            <div>Trading date: <span className="text-oa-text">{meta?.trading_date || "-"}</span></div>
            <div>Equities: <span className="text-oa-text">{meta?.row_count ?? rows.length}</span></div>
          </div>
        </div>

        <div className="rounded border border-oa-border bg-black">
          <div className="flex h-11 items-center border-b border-oa-border px-4 text-sm text-oa-muted">
            {loading ? (
              <div className="flex items-center gap-2">
                <Spinner color="light" />
                <span>Building latest OHLCV predictions...</span>
              </div>
            ) : error ? (
              <span className="text-red-200">{error}</span>
            ) : (
              <span>Latest generated recommendations</span>
            )}
          </div>

          <div className="overflow-auto">
            <table className="min-w-[1320px] w-full border-collapse text-left text-xs">
              <thead className="sticky top-0 bg-oa-panel text-oa-muted">
                <tr>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Rank</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Symbol</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Prediction</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Score</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Close</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">1D %</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">5D %</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">10D %</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">20D %</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Volume 20</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Volatility</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Risk</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Entry</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Stop</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Target 1</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Target 2</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Reason</th>
                </tr>
              </thead>

              <tbody className="text-oa-text">
                {!loading && !error && rows.length === 0 ? (
                  <tr>
                    <td className="px-3 py-6 text-center text-oa-muted" colSpan={17}>
                      No prediction rows found. OHLCV data may need to be collected first.
                    </td>
                  </tr>
                ) : null}

                {rows.map((row) => (
                  <tr key={`${row.instrument_key}-${row.trading_date}`} className="border-b border-oa-border/70 hover:bg-oa-card/60">
                    <td className="px-3 py-2 text-oa-muted">{row.rank_number || "-"}</td>
                    <td className="px-3 py-2 font-medium text-white">{row.trading_symbol || row.instrument_key}</td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex min-w-14 justify-center rounded border px-2 py-1 text-[11px] font-semibold ${getRecommendationClass(row.recommendation)}`}>
                        {row.recommendation || "HOLD"}
                      </span>
                    </td>
                    <td className="px-3 py-2">{formatNumber(row.prediction_score)}</td>
                    <td className="px-3 py-2">{formatPrice(row.close_price)}</td>
                    <td className="px-3 py-2">{formatNumber(row.return_1d)}</td>
                    <td className="px-3 py-2">{formatNumber(row.return_5d)}</td>
                    <td className="px-3 py-2">{formatNumber(row.return_10d)}</td>
                    <td className="px-3 py-2">{formatNumber(row.return_20d)}</td>
                    <td className="px-3 py-2">{formatNumber(row.volume_ratio_20)}</td>
                    <td className="px-3 py-2">{formatNumber(row.volatility_20)}</td>
                    <td className="px-3 py-2">{row.risk_level || "-"}</td>
                    <td className="px-3 py-2">{formatPrice(row.entry_price)}</td>
                    <td className="px-3 py-2">{formatPrice(row.stop_loss_price)}</td>
                    <td className="px-3 py-2">{formatPrice(row.target_1_price)}</td>
                    <td className="px-3 py-2">{formatPrice(row.target_2_price)}</td>
                    <td className="max-w-[360px] truncate px-3 py-2 text-oa-muted" title={row.reason || ""}>{row.reason || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
