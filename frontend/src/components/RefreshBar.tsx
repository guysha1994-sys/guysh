// frontend/src/components/RefreshBar.tsx
export function RefreshBar({
  lastUpdated,
  onRefresh,
}: {
  lastUpdated: Date | null;
  onRefresh: () => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "16px",
      }}
    >
      <span className="dim">
        {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : "Loading…"}
      </span>
      <button className="secondary" onClick={onRefresh}>
        Refresh
      </button>
    </div>
  );
}
