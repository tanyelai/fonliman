import { useEffect, useState } from "react";
import useSWR, { mutate } from "swr";

import { Modal } from "@/components/Modal";
import { postJSON } from "@/lib/api";
import { formatPercent, formatTL, returnColor, riskColor } from "@/lib/format";
import type { FundPreview, Group } from "@/lib/types";

interface Props {
  onClose: () => void;
}

// Two-step flow: enter code → live preview from TEFAS → assign group → save.
// The preview happens on a debounced 400ms timer so the user sees their
// fund take shape as they finish typing, but we don't hit TEFAS on every
// keystroke.
export function AddFundModal({ onClose }: Props) {
  const { data: groups } = useSWR<Group[]>("/api/groups");
  const [code, setCode] = useState("");
  const [preview, setPreview] = useState<FundPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [groupId, setGroupId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Debounced preview fetch.
  useEffect(() => {
    const cleaned = code.trim().toUpperCase();
    if (cleaned.length < 2) {
      setPreview(null);
      setPreviewError(null);
      setLoadingPreview(false);
      return;
    }
    setLoadingPreview(true);
    setPreviewError(null);
    const timer = setTimeout(async () => {
      try {
        const resp = await fetch(`/api/funds/preview/${cleaned}`);
        if (resp.status === 404) {
          setPreview(null);
          setPreviewError("Bu kodla bir fon bulunamadı.");
        } else if (!resp.ok) {
          setPreview(null);
          setPreviewError("Önizleme alınamadı, tekrar deneyin.");
        } else {
          setPreview(await resp.json());
          setPreviewError(null);
        }
      } catch {
        setPreviewError("Önizleme alınamadı.");
      } finally {
        setLoadingPreview(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [code]);

  async function onSubmit() {
    if (!preview) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await postJSON("/api/funds", { code: preview.code, group_id: groupId });
      mutate("/api/dashboard");
      mutate("/api/funds");
      onClose();
    } catch (e) {
      setSubmitError(String(e));
      setSubmitting(false);
    }
  }

  return (
    <Modal
      title="Fon ekle"
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} className="btn btn-ghost">İptal</button>
          <button
            onClick={onSubmit}
            disabled={!preview || submitting}
            className="btn btn-primary"
          >
            {submitting ? "Ekleniyor…" : "Ekle"}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-ink-500 dark:text-ink-400 mb-1">
            TEFAS Kodu
          </label>
          <input
            autoFocus
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="örn. AOY"
            maxLength={6}
            className="w-full px-3 py-2 rounded-lg
                       bg-ink-100 dark:bg-ink-900
                       border border-ink-200 dark:border-ink-700
                       text-ink-900 dark:text-ink-50
                       placeholder-ink-400 dark:placeholder-ink-500
                       focus:border-ink-400 dark:focus:border-ink-500
                       focus:ring-2 focus:ring-ink-300 dark:focus:ring-ink-600
                       focus:outline-none font-mono tabular tracking-tight"
          />
        </div>

        <div className="min-h-[120px]">
          {loadingPreview && (
            <div className="text-sm text-ink-400 animate-pulse-soft">TEFAS sorgulanıyor…</div>
          )}
          {previewError && <div className="text-sm text-negative">{previewError}</div>}
          {preview && !loadingPreview && (
            <div className="rounded-xl bg-ink-50 dark:bg-ink-900/60
                            border border-ink-200/70 dark:border-ink-800/70 p-3 space-y-2">
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="font-mono font-semibold">{preview.code}</span>
                  {preview.risk_score && (
                    <span className={`pill ${riskColor(preview.risk_score)}`}>R{preview.risk_score}</span>
                  )}
                </div>
                <div className="text-xs text-ink-600 dark:text-ink-400 mt-0.5">{preview.name}</div>
                {preview.tefas_category && (
                  <div className="text-[11px] text-ink-400 mt-0.5">{preview.tefas_category}</div>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <Stat label="Son fiyat" value={formatTL(preview.latest_price)} />
                <Stat label="1A" value={formatPercent(preview.return_1m, { signed: true })}
                      valueClass={returnColor(preview.return_1m)} />
                <Stat label="1Y" value={formatPercent(preview.return_1y, { signed: true })}
                      valueClass={returnColor(preview.return_1y)} />
              </div>
            </div>
          )}
        </div>

        <div>
          <label className="block text-xs font-medium text-ink-500 dark:text-ink-400 mb-1">
            Grup
          </label>
          <select
            value={groupId ?? ""}
            onChange={(e) => setGroupId(e.target.value ? Number(e.target.value) : null)}
            className="w-full px-3 py-2 rounded-lg
                       bg-ink-100 dark:bg-ink-900
                       border border-ink-200 dark:border-ink-700
                       text-ink-900 dark:text-ink-50
                       focus:border-ink-400 dark:focus:border-ink-500
                       focus:ring-2 focus:ring-ink-300 dark:focus:ring-ink-600
                       focus:outline-none"
          >
            <option value="">— Gruplandırılmamış —</option>
            {(groups ?? []).map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
          {(groups ?? []).length === 0 && (
            <p className="text-[11px] text-ink-400 mt-1">
              Henüz grup yok. Eklendikten sonra fonu bir gruba taşıyabilirsin.
            </p>
          )}
        </div>

        {submitError && <div className="text-sm text-negative">{submitError}</div>}
      </div>
    </Modal>
  );
}

function Stat({ label, value, valueClass = "" }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] text-ink-400">{label}</span>
      <span className={`tabular ${valueClass}`}>{value}</span>
    </div>
  );
}
