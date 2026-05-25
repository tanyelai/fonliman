import { Route, Routes } from "react-router-dom";

import { Header } from "@/components/Header";
import { Dashboard } from "@/pages/Dashboard";
import { FundDetail } from "@/pages/FundDetail";

export function App() {
  return (
    <div className="min-h-screen bg-ink-50 dark:bg-ink-950 text-ink-900 dark:text-ink-100">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/fon/:code" element={<FundDetail />} />
          {/* Geriye dönük: önceki sürüm /fund/:code yoluyla bookmark açtıysa */}
          <Route path="/fund/:code" element={<FundDetail />} />
        </Routes>
      </main>
    </div>
  );
}
