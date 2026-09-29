// frontend/src/pages/Indices.tsx
import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { addIndex, ApiError, getIndices, removeIndex } from "../api";
import type { WatchedIndex } from "../api";
import { usePolling } from "../hooks/usePolling";
import { PriceCell } from "../components/PriceCell";
import { RefreshBar } from "../components/RefreshBar";

export default function Indices() {
  const [indices, setIndices] = useState<WatchedIndex[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [symbol, setSymbol] = useState("");
  const [displayName, setDisplayName] = useState("");
  const navigate = useNavigate();

  const fetchIndices = useCallback(async () => {
    try {
      const data = await getIndices();
      setIndices(data);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login");
        return;
      }
      setError("Could not load indices.");
    }
  }, [navigate]);

  const { lastUpdated, refresh } = usePolling(fetchIndices);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!symbol.trim() || !displayName.trim()) return;
    try {
      await addIndex(symbol.trim(), displayName.trim());
      setSymbol("");
      setDisplayName("");
      await refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login");
        return;
      }
      setError("Could not add index.");
    }
  }

  async function handleRemove(sym: string) {
    try {
      await removeIndex(sym);
      await refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login");
        return;
      }
      setError("Could not remove index.");
    }
  }

  return (
    <div>
      <h1 style={{ fontFamily: "var(--font-mono)" }}>Indices</h1>
      <RefreshBar lastUpdated={lastUpdated} onRefresh={refresh} />
      {error && <p className="error-text">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Name</th>
            <th className="numeric">Price</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {indices.map((i) => (
            <tr
              key={i.symbol}
              onClick={() => navigate(`/trade/${i.symbol}`)}
              style={{ cursor: "pointer" }}
            >
              <td>{i.symbol}</td>
              <td>{i.display_name}</td>
              <td className="numeric">
                <PriceCell price={i.current_price} pctChange={i.pct_change} />
              </td>
              <td>
                <button
                  className="secondary"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemove(i.symbol);
                  }}
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <form onSubmit={handleAdd} style={{ marginTop: "24px" }}>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Symbol (e.g. SOXX)"
          required
          style={{ marginRight: "8px" }}
        />
        <input
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="Display name"
          required
          style={{ marginRight: "8px" }}
        />
        <button type="submit">Add index</button>
      </form>
    </div>
  );
}
