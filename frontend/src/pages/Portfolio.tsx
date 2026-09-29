// frontend/src/pages/Portfolio.tsx
import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, getPortfolio } from "../api";
import type { Position } from "../api";
import { usePolling } from "../hooks/usePolling";
import { PriceCell } from "../components/PriceCell";
import { RefreshBar } from "../components/RefreshBar";

export default function Portfolio() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newTicker, setNewTicker] = useState("");
  const navigate = useNavigate();

  const fetchPositions = useCallback(async () => {
    try {
      const data = await getPortfolio();
      setPositions(data);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login");
        return;
      }
      setError("Could not load your portfolio.");
    }
  }, [navigate]);

  const { lastUpdated, refresh } = usePolling(fetchPositions);

  function handleAddTicker(e: FormEvent) {
    e.preventDefault();
    const ticker = newTicker.trim().toUpperCase();
    if (!ticker) return;
    navigate(`/trade/${ticker}`);
  }

  return (
    <div>
      <h1 style={{ fontFamily: "var(--font-mono)" }}>Portfolio</h1>
      <RefreshBar lastUpdated={lastUpdated} onRefresh={refresh} />
      {error && <p className="error-text">{error}</p>}
      {positions.length === 0 && !error ? (
        <p className="dim">No open positions yet. Buy something from Recommendations.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th className="numeric">Qty</th>
              <th className="numeric">Entry</th>
              <th className="numeric">Stop</th>
              <th className="numeric">Price</th>
              <th className="numeric">P/L</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr
                key={p.id}
                onClick={() => navigate(`/trade/${p.ticker}`, { state: { position: p } })}
                style={{ cursor: "pointer" }}
              >
                <td>{p.ticker}</td>
                <td className="numeric">{p.quantity}</td>
                <td className="numeric">{p.entry_price.toFixed(2)}</td>
                <td className="numeric">{p.stop_loss.toFixed(2)}</td>
                <td className="numeric">
                  <PriceCell price={p.current_price} pctChange={p.pct_change} />
                </td>
                <td
                  className={`numeric ${
                    p.pnl_pct === null ? "" : p.pnl_pct >= 0 ? "positive" : "negative"
                  }`}
                >
                  {p.pnl_pct !== null
                    ? `${p.pnl_pct >= 0 ? "+" : ""}${p.pnl_pct.toFixed(2)}%`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form onSubmit={handleAddTicker} style={{ marginTop: "24px" }}>
        <input
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          placeholder="Ticker (e.g. AAPL)"
          required
          style={{ marginRight: "8px" }}
        />
        <button type="submit">Add position</button>
      </form>
    </div>
  );
}
