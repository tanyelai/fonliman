import { useState } from "react";

import { Modal } from "@/components/Modal";
import { deleteResource, patchJSON } from "@/lib/api";
import type { Group } from "@/lib/types";

interface Props {
  group: Group;
  onClose: () => void;
  onSaved: () => void;
}

// Curated palette — keeps groups visually distinguishable without exposing
// a full picker that would clash with the dashboard's restrained aesthetic.
const PALETTE = [
  "#6b7280", "#3b82f6", "#10b981", "#f59e0b",
  "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6",
];

export function EditGroupModal({ group, onClose, onSaved }: Props) {
  const [name, setName] = useState(group.name);
  const [color, setColor] = useState(group.color);
  const [targetPct, setTargetPct] = useState<string>(
    group.target_pct === null ? "" : String(group.target_pct),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSave() {
    setBusy(true);
    setError(null);
    try {
      const target = targetPct.trim() === "" ? null : Number(targetPct);
      await patchJSON(`/api/groups/${group.id}`, {
        name,
        color,
        target_pct: target,
        clear_target_pct: target === null,
      });
      onSaved();
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  async function onDelete() {
    if (!confirm(`"${group.name}" grubunu silmek istediğinden emin misin? Fonlar gruplandırılmamış olarak kalır.`)) return;
    setBusy(true);
    try {
      await deleteResource(`/api/groups/${group.id}`);
      onSaved();
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  return (
    <Modal
      title="Grubu düzenle"
      onClose={onClose}
      footer={
        <>
          <button onClick={onDelete} disabled={busy} className="btn btn-ghost text-negative">
            Sil
          </button>
          <div className="flex-1" />
          <button onClick={onClose} className="btn btn-ghost">İptal</button>
          <button onClick={onSave} disabled={busy} className="btn btn-primary">
            {busy ? "Kaydediliyor…" : "Kaydet"}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-ink-500 dark:text-ink-400 mb-1">İsim</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-ink-100 dark:bg-ink-900
                       border border-ink-200 dark:border-ink-700
                       text-ink-900 dark:text-ink-50
                       placeholder-ink-400 dark:placeholder-ink-500
                       focus:border-ink-400 dark:focus:border-ink-500
                       focus:ring-2 focus:ring-ink-300 dark:focus:ring-ink-600
                       focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-ink-500 dark:text-ink-400 mb-1">Renk</label>
          <div className="flex flex-wrap gap-2">
            {PALETTE.map((c) => (
              <button
                key={c}
                onClick={() => setColor(c)}
                className={`w-7 h-7 rounded-full transition-transform
                            ${color === c ? "scale-110 ring-2 ring-offset-2 ring-ink-400 dark:ring-ink-500" : ""}`}
                style={{ backgroundColor: c }}
                aria-label={c}
              />
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-ink-500 dark:text-ink-400 mb-1">
            Hedef ağırlık (%) — opsiyonel
          </label>
          <input
            type="number"
            min="0"
            max="100"
            step="1"
            value={targetPct}
            onChange={(e) => setTargetPct(e.target.value)}
            placeholder="örn. 30"
            className="w-full px-3 py-2 rounded-lg bg-ink-100 dark:bg-ink-900
                       border border-ink-200 dark:border-ink-700
                       text-ink-900 dark:text-ink-50
                       placeholder-ink-400 dark:placeholder-ink-500
                       focus:border-ink-400 dark:focus:border-ink-500
                       focus:ring-2 focus:ring-ink-300 dark:focus:ring-ink-600
                       focus:outline-none tabular"
          />
          <p className="text-[11px] text-ink-400 mt-1">
            Portföydeki hedef oran. Boş bırakırsan drift uyarısı çalışmaz.
          </p>
        </div>

        {error && <div className="text-sm text-negative">{error}</div>}
      </div>
    </Modal>
  );
}
