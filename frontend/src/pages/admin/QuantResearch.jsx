import { useCallback, useEffect, useState } from "react";
import { RefreshCcw } from "lucide-react";

import { getAutomatedStockPredictions, refreshAutomatedStockPredictions } from "../../api/quantResearchApi";
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

  const [refreshing, setRefreshing] = useState(false);

  const loadPredictions = useCallback(async (showLoading = false) => {
    if (showLoading) {
      setLoading(true);
    }
    setError("");

    try {
      const response = await getAutomatedStockPredictions();
      const data = response.data?.data || {};

      setRows(Array.isArray(data.rows) ? data.rows : []);
      setMeta(data);
      setRefreshing(Boolean(data.active_run));
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Unable to load predictions.");
      setRows([]);
      setMeta(null);
      setRefreshing(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPredictions(true);
  }, [loadPredictions]);

  useEffect(() => {
    if (!meta?.active_run) {
      return undefined;
    }

    const pollTimer = window.setTimeout(() => loadPredictions(false), 5000);
    return () => window.clearTimeout(pollTimer);
  }, [loadPredictions, meta?.active_run]);

  async function handleRefreshPredictions() {
    setRefreshing(true);
    setError("");

    try {
      const response = await refreshAutomatedStockPredictions();
      const data = response.data?.data || {};
      setMeta((current) => ({
        ...(current || {}),
        ...data,
        active_run: data.active_run || current?.active_run || { status: "running", message: data.message || "Prediction refresh queued." }
      }));
      window.setTimeout(() => loadPredictions(false), 1000);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Unable to refresh predictions.");
      setRefreshing(false);
    }
  }

  const activeRunMessage = meta?.active_run?.message || "Prediction refresh is running.";
  const statusText = meta?.active_run
    ? `Building fresh predictions: ${activeRunMessage}`
    : meta?.cache_status === "missing"
      ? "No saved predictions found. Use Refresh Predictions to build fresh data."
      : "Latest saved recommendations from DB";

  return (
    <MainLayout>
      <div className="space-y-4 px-4 py-4 lg:px-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold text-white">Predictions</h1>
            <p className="mt-1 text-sm text-oa-muted">
              Automated OHLCV, ML, and deep-learning predictions with dynamic model-weighted recommendations.
            </p>
          </div>

          <div className="flex flex-col items-end gap-2">
            <button
              type="button"
              onClick={handleRefreshPredictions}
              disabled={refreshing}
              className="inline-flex h-9 items-center gap-2 rounded border border-oa-border bg-oa-card px-3 text-xs font-semibold text-oa-text transition hover:border-sky-500/60 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
              title="Build fresh predictions and replace the saved DB cache"
            >
              <RefreshCcw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              <span>{refreshing ? "Building..." : "Refresh Predictions"}</span>
            </button>

            <div className="text-right text-xs text-oa-muted">
            <div>Trading date: <span className="text-oa-text">{meta?.trading_date || "-"}</span></div>
            <div>Equities: <span className="text-oa-text">{meta?.row_count ?? rows.length}</span></div>
            <div>
              Model weights: <span className="text-oa-text">T {formatNumber((meta?.weights?.technical || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / ML {formatNumber((meta?.weights?.ml || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / Deep {formatNumber((meta?.weights?.deep_learning || 0) * 100, 0)}%</span>
            </div>
            <div>
              Input weights: <span className="text-oa-text">Ret {formatNumber((meta?.technical_profile?.component_weights?.return || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / Vol {formatNumber((meta?.technical_profile?.component_weights?.volume || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / Trend {formatNumber((meta?.technical_profile?.component_weights?.trend || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / Risk {formatNumber((meta?.technical_profile?.component_weights?.risk || 0) * 100, 0)}%</span>
            </div>
            <div>
              Indicators: <span className="text-oa-text">R1 {formatNumber((meta?.technical_profile?.indicator_weights?.return_1d || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / R5 {formatNumber((meta?.technical_profile?.indicator_weights?.return_5d || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / R10 {formatNumber((meta?.technical_profile?.indicator_weights?.return_10d || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / R20 {formatNumber((meta?.technical_profile?.indicator_weights?.return_20d || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / Vol {formatNumber((meta?.technical_profile?.indicator_weights?.volume_ratio_20 || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / Vlt {formatNumber((meta?.technical_profile?.indicator_weights?.volatility_20 || 0) * 100, 0)}%</span>
            </div>
            <div>
              Classic: <span className="text-oa-text">RSI {formatNumber((meta?.technical_profile?.indicator_weights?.rsi_14 || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / MACD {formatNumber(((meta?.technical_profile?.indicator_weights?.macd_line || 0) + (meta?.technical_profile?.indicator_weights?.macd_signal || 0) + (meta?.technical_profile?.indicator_weights?.macd_histogram || 0)) * 100, 0)}%</span>
              <span className="text-oa-text"> / BB {formatNumber(((meta?.technical_profile?.indicator_weights?.bollinger_position || 0) + (meta?.technical_profile?.indicator_weights?.bollinger_width || 0)) * 100, 0)}%</span>
              <span className="text-oa-text"> / ATR {formatNumber((meta?.technical_profile?.indicator_weights?.atr_14_pct || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / Stoch {formatNumber(((meta?.technical_profile?.indicator_weights?.stochastic_k_14 || 0) + (meta?.technical_profile?.indicator_weights?.stochastic_d_3 || 0)) * 100, 0)}%</span>
              <span className="text-oa-text"> / ADX {formatNumber((meta?.technical_profile?.indicator_weights?.adx_14 || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / MFI {formatNumber((meta?.technical_profile?.indicator_weights?.mfi_14 || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / CMF {formatNumber((meta?.technical_profile?.indicator_weights?.chaikin_money_flow_20 || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / VWAP {formatNumber((meta?.technical_profile?.indicator_weights?.vwap_distance_20 || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / Don {formatNumber((meta?.technical_profile?.indicator_weights?.donchian_position_20 || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / OBV {formatNumber((meta?.technical_profile?.indicator_weights?.obv_slope_20 || 0) * 100, 0)}%</span>
              <span className="text-oa-text"> / PVT {formatNumber((meta?.technical_profile?.indicator_weights?.pvt_slope_20 || 0) * 100, 0)}%</span>
            </div>
          </div>
        </div>
        </div>

        <div className="rounded border border-oa-border bg-black">
          <div className="flex h-11 items-center border-b border-oa-border px-4 text-sm text-oa-muted">
            {loading ? (
              <div className="flex items-center gap-2">
                <Spinner color="light" />
                <span>Loading cached predictions...</span>
              </div>
            ) : error ? (
              <span className="text-red-200">{error}</span>
            ) : (
              <span>{statusText}</span>
            )}
          </div>

          <div className="overflow-auto">
            <table className="min-w-[1500px] w-full border-collapse text-left text-xs">
              <thead className="sticky top-0 bg-oa-panel text-oa-muted">
                <tr>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Rank</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Symbol</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Prediction</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Score</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Tech</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">ML</th>
                  <th className="border-b border-oa-border px-3 py-2 font-medium">Deep</th>
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
                    <td className="px-3 py-6 text-center text-oa-muted" colSpan={20}>
                      No saved prediction rows found. Click Refresh Predictions to build fresh data.
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
                    <td className="px-3 py-2">{formatNumber(row.technical_score)}</td>
                    <td className="px-3 py-2">{formatNumber(row.ml_score)}</td>
                    <td className="px-3 py-2">{formatNumber(row.deep_learning_score)}</td>
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
