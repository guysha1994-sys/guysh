import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import Login from "./pages/Login";
import Portfolio from "./pages/Portfolio";
import Recommendations from "./pages/Recommendations";
import Indices from "./pages/Indices";
import Trade from "./pages/Trade";

function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <NavBar />
      <main style={{ padding: "20px", maxWidth: "960px", margin: "0 auto" }}>
        {children}
      </main>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/portfolio"
          element={
            <Layout>
              <Portfolio />
            </Layout>
          }
        />
        <Route
          path="/recommendations"
          element={
            <Layout>
              <Recommendations />
            </Layout>
          }
        />
        <Route
          path="/indices"
          element={
            <Layout>
              <Indices />
            </Layout>
          }
        />
        <Route
          path="/trade/:ticker"
          element={
            <Layout>
              <Trade />
            </Layout>
          }
        />
        <Route path="*" element={<Navigate to="/portfolio" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
