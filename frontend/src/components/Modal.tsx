import { useEffect } from "react";
import { createPortal } from "react-dom";

interface Props {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: "sm" | "md";
}

// Lightweight modal — Headless UI / Radix would be overkill for two modals.
// Click backdrop or Escape to dismiss; focus management is delegated to
// native autofocus on inputs.
//
// Renders through a portal to document.body so the modal escapes the
// Header's stacking context (the header uses backdrop-blur, which creates
// a new stacking context and would otherwise trap the modal beneath it).
export function Modal({ title, onClose, children, footer, size = "md" }: Props) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    // Lock background scroll while the modal is open.
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  const width = size === "sm" ? "max-w-sm" : "max-w-md";

  return createPortal(
    <div
      className="fixed inset-0 z-[100] bg-ink-950/60 dark:bg-black/70
                 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`w-full ${width} rounded-2xl shadow-2xl
                    bg-white dark:bg-ink-800
                    ring-1 ring-ink-200 dark:ring-ink-700`}
      >
        <header className="flex items-center justify-between
                          px-5 py-3 border-b border-ink-200/80 dark:border-ink-700">
          <h2 className="font-semibold tracking-tight text-ink-900 dark:text-ink-50">
            {title}
          </h2>
          <button onClick={onClose} className="btn btn-ghost h-7 w-7 p-0">
            <CloseIcon />
          </button>
        </header>
        <div className="p-5">{children}</div>
        {footer && (
          <footer className="flex justify-end gap-2 px-5 py-3
                            border-t border-ink-200/80 dark:border-ink-700">
            {footer}
          </footer>
        )}
      </div>
    </div>,
    document.body,
  );
}

function CloseIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}
