import { useState } from "react";
import {
  buildQuantFeatures,
  buildQuantLabels,
  buildQuantRankings,
  discoverQuantPatterns,
  getQuantResearchReadiness,
  runQuantBacktest
} from "../../api/quantResearchApi";
import Spinner from "../../components/common/Spinner";

export default function QuantResearch() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function runAction(action) {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await action();
      setResult(response.data);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Action failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-white">Quant Research</h1>
        <p className="mt-1 text-sm text-oa-muted">
          Research assistant for features, labels, pattern discovery, backtesting, rankings, and ML readiness.
        </p>
      </div>

      <div className="rounded border border-oa-border bg-black p-4">
        <div className="flex flex-wrap gap-2">
          <button className="rounded border border-oa-border px-3 py-2 text-sm text-oa-muted hover:bg-oa-card hover:text-white" onClick={() => runAction(getQuantResearchReadiness)} disabled={loading}>Check Readiness</button>
          <button className="rounded border border-oa-border px-3 py-2 text-sm text-oa-muted hover:bg-oa-card hover:text-white" onClick={() => runAction(buildQuantFeatures)} disabled={loading}>Build Features</button>
          <button className="rounded border border-oa-border px-3 py-2 text-sm text-oa-muted hover:bg-oa-card hover:text-white" onClick={() => runAction(buildQuantLabels)} disabled={loading}>Build Labels</button>
          <button className="rounded border border-oa-border px-3 py-2 text-sm text-oa-muted hover:bg-oa-card hover:text-white" onClick={() => runAction(discoverQuantPatterns)} disabled={loading}>Discover Patterns</button>
          <button className="rounded border border-oa-border px-3 py-2 text-sm text-oa-muted hover:bg-oa-card hover:text-white" onClick={() => runAction(runQuantBacktest)} disabled={loading}>Run Backtest</button>
          <button className="rounded border border-oa-border px-3 py-2 text-sm text-oa-muted hover:bg-oa-card hover:text-white" onClick={() => runAction(buildQuantRankings)} disabled={loading}>Build Rankings</button>
        </div>

        {loading ? <div className="mt-4"><Spinner /></div> : null}
        {error ? <div className="mt-4 rounded border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">{error}</div> : null}
        {result ? <pre className="mt-4 overflow-auto rounded border border-oa-border bg-oa-panel p-3 text-xs text-oa-muted">{JSON.stringify(result, null, 2)}</pre> : null}
      </div>
    </div>
  );
}
