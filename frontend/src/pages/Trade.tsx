// frontend/src/pages/Trade.tsx
import { useState } from "react";
import type { FormEvent } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { addToPosition, ApiError, buyPosition, sellPosition, updateStopLoss } from "../api";
import type { Position } from "../api";

type TradeState = { position?: Position };

export default function Trade() {
  const { ticker } = useParams<{ ticker: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const position = (location.state as TradeState | null)?.position;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleAuthError(err: unknown): Promise<boolean> {
    if (err instanceof ApiError && err.status === 401) {
      navigate("/login");
      return true;
    }
    return false;
  }

  async function handleBuy(entryPrice: number, quantity: number, stopLoss: number) {
    setBusy(true);
    setError(null);
    try {
      await buyPosition(ticker!, entryPrice, quantity, stopLoss);
      navigate("/portfolio");
    } catch (err) {
      if (!(await handleAuthError(err))) {
        setError("Could not open position. Check your inputs and try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleAddToPosition(quantity: number, price: number) {
    if (!position) return;
    setBusy(true);
    setError(null);
    try {
      await addToPosition(position.id, quantity, price);
      navigate("/portfolio");
    } catch (err) {
      if (!(await handleAuthError(err))) {
        setError("Could not add to position. Check your inputs and try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleUpdateStopLoss(stopLoss: number) {
    if (!position) return;
    setBusy(true);
    setError(null);
    try {
      await updateStopLoss(position.id, stopLoss);
      navigate("/portfolio");
    } catch (err) {
      if (!(await handleAuthError(err))) {
        setError("Could not update stop-loss. Check your input and try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleSell() {
    if (!position) return;
    setBusy(true);
    setError(null);
    try {
      await sellPosition(position.id);
      navigate("/portfolio");
    } catch (err) {
      if (!(await handleAuthError(err))) {
        setError("Could not sell position. Try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  if (position) {
    return (
      <div style={{ maxWidth: "420px" }}>
        <h1 style={{ fontFamily: "var(--font-mono)" }}>{position.ticker}</h1>
        <p className="dim">
          {position.quantity} shares @ avg {position.entry_price.toFixed(2)} · stop{" "}
          {position.stop_loss.toFixed(2)}
        </p>

        <section style={{ marginTop: "24px" }}>
          <h2 style={{ fontSize: "15px" }}>Buy more</h2>
          <AddForm onSubmit={handleAddToPosition} busy={busy} />
        </section>

        <section style={{ marginTop: "24px" }}>
          <h2 style={{ fontSize: "15px" }}>Update stop-loss</h2>
          <StopLossForm
            onSubmit={handleUpdateStopLoss}
            initialValue={position.stop_loss}
            busy={busy}
          />
        </section>

        <section style={{ marginTop: "24px" }}>
          <button className="secondary" onClick={handleSell} disabled={busy}>
            Sell entire position
          </button>
        </section>

        {error && <p className="error-text">{error}</p>}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "420px" }}>
      <h1 style={{ fontFamily: "var(--font-mono)" }}>Buy {ticker}</h1>
      <BuyForm onSubmit={handleBuy} busy={busy} />
      {error && <p className="error-text">{error}</p>}
    </div>
  );
}

function BuyForm({
  onSubmit,
  busy,
}: {
  onSubmit: (entryPrice: number, quantity: number, stopLoss: number) => void;
  busy: boolean;
}) {
  const [entryPrice, setEntryPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [stopLoss, setStopLoss] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(Number(entryPrice), Number(quantity), Number(stopLoss));
      }}
    >
      <label className="dim">Entry price</label>
      <input
        value={entryPrice}
        onChange={(e) => setEntryPrice(e.target.value)}
        type="number"
        step="0.01"
        min="0.01"
        required
        style={{ display: "block", width: "100%", marginBottom: "12px" }}
      />
      <label className="dim">Quantity</label>
      <input
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        type="number"
        step="0.0001"
        min="0.0001"
        required
        style={{ display: "block", width: "100%", marginBottom: "12px" }}
      />
      <label className="dim">Stop-loss</label>
      <input
        value={stopLoss}
        onChange={(e) => setStopLoss(e.target.value)}
        type="number"
        step="0.01"
        min="0.01"
        required
        style={{ display: "block", width: "100%", marginBottom: "16px" }}
      />
      <button type="submit" disabled={busy}>
        Buy
      </button>
    </form>
  );
}

function AddForm({
  onSubmit,
  busy,
}: {
  onSubmit: (quantity: number, price: number) => void;
  busy: boolean;
}) {
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");

  return (
    <form
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        onSubmit(Number(quantity), Number(price));
      }}
    >
      <input
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        type="number"
        step="0.0001"
        min="0.0001"
        placeholder="Quantity"
        required
        style={{ marginRight: "8px" }}
      />
      <input
        value={price}
        onChange={(e) => setPrice(e.target.value)}
        type="number"
        step="0.01"
        min="0.01"
        placeholder="Price"
        required
        style={{ marginRight: "8px" }}
      />
      <button type="submit" disabled={busy}>
        Add
      </button>
    </form>
  );
}

function StopLossForm({
  onSubmit,
  initialValue,
  busy,
}: {
  onSubmit: (stopLoss: number) => void;
  initialValue: number;
  busy: boolean;
}) {
  const [stopLoss, setStopLoss] = useState(String(initialValue));

  return (
    <form
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        onSubmit(Number(stopLoss));
      }}
    >
      <input
        value={stopLoss}
        onChange={(e) => setStopLoss(e.target.value)}
        type="number"
        step="0.01"
        min="0.01"
        required
        style={{ marginRight: "8px" }}
      />
      <button type="submit" disabled={busy}>
        Update
      </button>
    </form>
  );
}
