import { useState } from "react";
import useSWR, { mutate } from "swr";

import { CreateGroupModal } from "@/components/CreateGroupModal";
import { EditGroupModal } from "@/components/EditGroupModal";
import { GroupCard } from "@/components/GroupCard";
import type { DashboardPayload, Group } from "@/lib/types";

export function Dashboard() {
  const { data, error, isLoading } = useSWR<DashboardPayload>(
    "/api/dashboard",
    {
      // Whenever there's at least one fund whose price hasn't landed (just
      // added → backfill in progress, or sync mid-flight), poll every 2.5 s
      // so the user doesn't need to refresh.
      refreshInterval: (latest) =>
        latest && hasPendingFund(latest) ? 2500 : 0,
    },
  );
  const [editGroup, setEditGroup] = useState<Group | null>(null);
  const [showCreateGroup, setShowCreateGroup] = useState(false);

  if (isLoading && !data) return <DashboardSkeleton />;
  if (error) return <ErrorState />;
  if (!data) return null;

  const orderedGroups = [...data.groups].sort((a, b) => a.sort_order - b.sort_order);
  const ungrouped = data.funds_by_group["ungrouped"] ?? [];
  const totalFunds = Object.values(data.funds_by_group).reduce((s, a) => s + a.length, 0);

  if (orderedGroups.length === 0 && totalFunds === 0) {
    return (
      <>
        <EmptyState onCreateGroup={() => setShowCreateGroup(true)} />
        {showCreateGroup && (
          <CreateGroupModal
            onClose={() => setShowCreateGroup(false)}
            onCreated={() => {
              mutate("/api/groups");
              mutate("/api/dashboard");
              setShowCreateGroup(false);
            }}
          />
        )}
      </>
    );
  }

  return (
    <>
      <div className="space-y-4">
        {orderedGroups.map((group) => (
          <GroupCard
            key={group.id}
            group={group}
            funds={data.funds_by_group[String(group.id)] ?? []}
            onEdit={setEditGroup}
          />
        ))}
        {ungrouped.length > 0 && (
          <GroupCard group={null} funds={ungrouped} />
        )}

        {/* Subtle "yeni grup" tile — feels native to the layout, not a button shoved in the header. */}
        <button
          onClick={() => setShowCreateGroup(true)}
          className="w-full rounded-2xl py-3 text-sm
                     border border-dashed
                     border-ink-300 dark:border-ink-700
                     text-ink-500 dark:text-ink-400
                     hover:border-ink-400 dark:hover:border-ink-500
                     hover:text-ink-700 dark:hover:text-ink-200
                     hover:bg-ink-100/40 dark:hover:bg-ink-900/40
                     transition-colors"
        >
          + Yeni grup
        </button>
      </div>

      {editGroup && (
        <EditGroupModal
          group={editGroup}
          onClose={() => setEditGroup(null)}
          onSaved={() => {
            mutate("/api/dashboard");
            mutate("/api/groups");
            setEditGroup(null);
          }}
        />
      )}
      {showCreateGroup && (
        <CreateGroupModal
          onClose={() => setShowCreateGroup(false)}
          onCreated={() => {
            mutate("/api/groups");
            mutate("/api/dashboard");
            setShowCreateGroup(false);
          }}
        />
      )}
    </>
  );
}

function hasPendingFund(data: DashboardPayload): boolean {
  for (const arr of Object.values(data.funds_by_group)) {
    for (const f of arr) {
      if (f.latest_price === null) return true;
    }
  }
  return false;
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      {[0, 1].map((i) => (
        <div key={i} className="card p-4 space-y-3 animate-pulse-soft">
          <div className="h-5 w-32 bg-ink-100 dark:bg-ink-800 rounded" />
          <div className="h-12 bg-ink-100 dark:bg-ink-800 rounded" />
          <div className="h-12 bg-ink-100 dark:bg-ink-800 rounded" />
        </div>
      ))}
    </div>
  );
}

function ErrorState() {
  return (
    <div className="card p-8 text-center">
      <h2 className="font-semibold mb-2">Veri yüklenemedi</h2>
      <p className="text-sm text-ink-500">
        Backend cevap vermiyor. Birkaç saniye sonra tekrar dene.
      </p>
    </div>
  );
}

function EmptyState({ onCreateGroup }: { onCreateGroup: () => void }) {
  return (
    <div className="card p-10 text-center">
      <h2 className="font-semibold text-lg mb-2">Henüz fon eklenmemiş</h2>
      <p className="text-sm text-ink-500 dark:text-ink-400 max-w-md mx-auto mb-6">
        Önce takip etmek istediğin fonları gruplara ayır (ABD Hisse, BIST,
        Para Piyasası gibi). Sonra sağ üstteki <span className="font-medium text-ink-900 dark:text-ink-100">+ Fon ekle</span> ile
        TEFAS kodunu (örn. AOY, BDS, TP2) girersin.
      </p>
      <button onClick={onCreateGroup} className="btn btn-primary">
        + Önce bir grup oluştur
      </button>
    </div>
  );
}
