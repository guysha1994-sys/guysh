import { NavLink } from "react-router-dom";
import type { CSSProperties } from "react";

export default function NavBar() {
  return (
    <nav
      style={{
        display: "flex",
        alignItems: "center",
        gap: "24px",
        padding: "14px 20px",
        borderBottom: "1px solid var(--border)",
        fontFamily: "var(--font-mono)",
      }}
    >
      <span style={{ color: "var(--accent)", fontWeight: 600 }}>STOCKER</span>
      <NavLink to="/portfolio" style={navLinkStyle}>
        Portfolio
      </NavLink>
      <NavLink to="/recommendations" style={navLinkStyle}>
        Recommendations
      </NavLink>
      <NavLink to="/indices" style={navLinkStyle}>
        Indices
      </NavLink>
    </nav>
  );
}

function navLinkStyle({ isActive }: { isActive: boolean }): CSSProperties {
  return {
    color: isActive ? "var(--accent)" : "var(--text-dim)",
    fontSize: "14px",
  };
}
