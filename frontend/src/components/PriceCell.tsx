// frontend/src/components/PriceCell.tsx
import { useEffect, useRef, useState } from "react";

export function PriceCell({
  price,
  pctChange,
}: {
  price: number | null;
  pctChange: number | null;
}) {
  const [flash, setFlash] = useState(false);
  const previous = useRef<number | null>(price);

  useEffect(() => {
    if (previous.current !== null && price !== null && previous.current !== price) {
      setFlash(true);
      const timeout = setTimeout(() => setFlash(false), 600);
      previous.current = price;
      return () => clearTimeout(timeout);
    }
    previous.current = price;
  }, [price]);

  if (price === null) {
    return <span className="dim">—</span>;
  }

  const colorClass = pctChange === null ? "" : pctChange >= 0 ? "positive" : "negative";

  return (
    <span className={flash ? "price-flash" : ""}>
      {price.toFixed(2)}
      {pctChange !== null && (
        <span className={colorClass} style={{ marginLeft: "8px", fontSize: "13px" }}>
          {pctChange >= 0 ? "+" : ""}
          {pctChange.toFixed(2)}%
        </span>
      )}
    </span>
  );
}
