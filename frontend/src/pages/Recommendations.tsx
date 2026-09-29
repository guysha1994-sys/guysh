// frontend/src/pages/Recommendations.tsx
import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, getRecommendations } from "../api";
import type { RecommendationResult } from "../api";
import { usePolling } from "../hooks/usePolling";
import { PriceCell } from "../components/PriceCell";
import { RefreshBar } from "../components/RefreshBar";

export default function Recommendations() {
  const [runDate, setRunDate] = useState<string | null>(null);
  const [results, setResults] = useState<RecommendationResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchRecommendations = useCallback(async () => {
    try {
      const data = await getRecommendations();
      setRunDate(data.run_date);
      setResults(data.results);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login");
        return;
      }
      setError("Could not load recommendations.");
    }
  }, [navigate]);

  const { lastUpdated, refresh } = usePolling(fetchRecommendations);

  return (
    <div>
      <h1 style={{ fontFamily: "var(--font-mono)" }}>Recommendations</h1>
      <p className="dim">{runDate ? `Screener run: ${runDate}` : "No screener run yet."}</p>
      <RefreshBar lastUpdated={lastUpdated} onRefresh={refresh} />
      {error && <p className="error-text">{error}</p>}
      {results.length === 0 && !error ? (
        <p className="dim">Nothing qualifies yet — check back after the next screener run.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th className="numeric">Price</th>
              <th className="numeric">Score</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr
                key={r.ticker}
                onClick={() => navigate(`/trade/${r.ticker}`)}
                style={{ cursor: "pointer" }}
              >
                <td>{r.ticker}</td>
                <td className="numeric">
                  <PriceCell price={r.current_price} pctChange={r.pct_change} />
                </td>
                <td className="numeric">{r.score.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
