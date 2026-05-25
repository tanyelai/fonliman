import { useState } from "react";

import { Modal } from "@/components/Modal";
import { postJSON } from "@/lib/api";
import type { Group } from "@/lib/types";

interface Props {
  onClose: () => void;
  onCreated: (group: Group) => void;
}

// Same curated palette used in EditGroupModal — consistency matters.
const PALETTE = [
  "#6b7280", "#3b82f6", "#10b981", "#f59e0b",
  "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6",
];

// A starter handful — feels less empty than a blank suggestion list.
const PRESETS = [
  "ABD Hisse", "BIST", "Para Piyasası", "Kıymetli Maden",
  "Tahvil", "Fon Sepeti",
];

export function CreateGroupModal({ onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [color, setColor] = useState(PALETTE[1]);
  const [targetPct, setTargetPct] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSave() {
    if (!name.trim()) {
      setError("Bir grup adı yaz.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const target = targetPct.trim() === "" ? null : Number(targetPct);
      const g = await postJSON<Group>("/api/groups", { name: name.trim(), color, target_pct: target });
      onCreated(g);
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  return (
    <Modal
      title="Yeni grup"
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} className="btn btn-ghost">İptal</button>
          <button onClick={onSave} disabled={busy} className="btn btn-primary">
            {busy ? "Oluşturuluyor…" : "Oluştur"}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-ink-500 dark:text-ink-400 mb-1">
            Grup adı
          </label>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="örn. ABD Hisse"
            className="w-full px-3 py-2 rounded-lg bg-ink-100 dark:bg-ink-900
                       border border-ink-200 dark:border-ink-700
                       text-ink-900 dark:text-ink-50
                       placeholder-ink-400 dark:placeholder-ink-500
                       focus:border-ink-400 dark:focus:border-ink-500
                       focus:ring-2 focus:ring-ink-300 dark:focus:ring-ink-600
                       focus:outline-none"
          />
          <div className="flex flex-wrap gap-1 mt-2">
            {PRESETS.filter((p) => !name || p.toLowerCase().startsWith(name.toLowerCase())).map((p) => (
              <button
                key={p}
                onClick={() => setName(p)}
                className="text-[11px] px-2 py-0.5 rounded-md
                           bg-ink-100 dark:bg-ink-800
                           hover:bg-ink-200 dark:hover:bg-ink-700
                           text-ink-600 dark:text-ink-300"
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-ink-500 dark:text-ink-400 mb-1">
            Renk
          </label>
          <div className="flex flex-wrap gap-2">
            {PALETTE.map((c) => (
              <button
                key={c}
                onClick={() => setColor(c)}
                className={`w-7 h-7 rounded-full transition-transform
                            ${color === c ? "scale-110 ring-2 ring-offset-2 ring-offset-ink-50 dark:ring-offset-ink-800 ring-ink-400 dark:ring-ink-300" : ""}`}
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
