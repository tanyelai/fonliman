import { useState } from "react";
import { Link } from "react-router-dom";
import useSWR, { mutate } from "swr";

import { postJSON } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";
import type { HealthResponse } from "@/lib/types";

import { AddFundModal } from "./AddFundModal";

export function Header() {
  const { data: health } = useSWR<HealthResponse>("/api/health", {
    // Header is mounted everywhere — poll for sync state so the user can
    // see "manual refresh" pulses end without leaving the page.
    refreshInterval: 5000,
  });
  const [showAdd, setShowAdd] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const syncStatus = health?.last_sync?.status;
  const isRunning = syncStatus === "running" || refreshing;
  const lastSyncAt = health?.last_sync?.finished_at ?? health?.last_sync?.started_at;

  async function onRefresh() {
    setRefreshing(true);
    try {
      await postJSON("/api/refresh", {});
      // Slight delay so the running indicator has time to register.
      setTimeout(() => {
        mutate("/api/health");
        mutate("/api/dashboard");
        setRefreshing(false);
      }, 1500);
    } catch {
      setRefreshing(false);
    }
  }

  return (
    <header className="border-b border-ink-200/70 dark:border-ink-900 bg-white/80 dark:bg-ink-950/80 backdrop-blur-md sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group">
          <Logo className="text-positive" />
          <div className="font-semibold tracking-tight text-lg">fonliman</div>
        </Link>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-2 text-xs text-ink-500 dark:text-ink-400 mr-2">
            <SyncIndicator running={isRunning} status={syncStatus} />
            <span>{isRunning ? "güncelleniyor…" : `son: ${formatRelativeTime(lastSyncAt)}`}</span>
          </div>
          <button
            onClick={onRefresh}
            disabled={isRunning}
            title="Şimdi güncelle"
            className="btn btn-ghost"
          >
            <RefreshIcon className={isRunning ? "animate-spin" : ""} />
          </button>
          <button onClick={() => setShowAdd(true)} className="btn btn-primary">
            <span className="text-base leading-none">+</span>
            <span className="hidden sm:inline">Fon ekle</span>
          </button>
        </div>
      </div>
      {showAdd && <AddFundModal onClose={() => setShowAdd(false)} />}
    </header>
  );
}

function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={`w-7 h-7 ${className}`}>
      <path d="M6 22 L11 14 L16 18 L21 9 L26 22 Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx="21" cy="9" r="1.8" fill="currentColor" />
    </svg>
  );
}

function RefreshIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={`w-4 h-4 ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M23 4v6h-6" />
      <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
    </svg>
  );
}

function SyncIndicator({ running, status }: { running: boolean; status?: string }) {
  if (running) return <span className="w-2 h-2 rounded-full bg-warning animate-pulse-soft" />;
  if (status === "error") return <span className="w-2 h-2 rounded-full bg-negative" />;
  if (status === "success") return <span className="w-2 h-2 rounded-full bg-positive" />;
  return <span className="w-2 h-2 rounded-full bg-ink-300 dark:bg-ink-700" />;
}
