import { useEffect, useState } from "react";

export const GAME_URL = "https://motions.games/";

export function openFitnessGameWindow() {
  const popup = window.open(
    GAME_URL,
    "juno-67-speed-game",
    "popup=yes,width=520,height=820,left=80,top=60,menubar=no,toolbar=no,location=yes,status=no,scrollbars=yes,resizable=yes"
  );

  if (popup) {
    popup.focus?.();
    return true;
  }

  // Browser popup blockers may reject window.open. Opening with _blank from a
  // user click is the next safest fallback and keeps the dashboard page alive.
  const fallbackAnchor = document.createElement("a");
  fallbackAnchor.href = GAME_URL;
  fallbackAnchor.target = "_blank";
  fallbackAnchor.rel = "noopener noreferrer";
  fallbackAnchor.style.display = "none";
  document.body.appendChild(fallbackAnchor);
  fallbackAnchor.click();
  fallbackAnchor.remove();
  return false;
}

export default function FitnessGameModal({ open, onClose, launchMessage = "" }) {
  const [message, setMessage] = useState("");
  const [iframeFailed, setIframeFailed] = useState(false);
  const [showEmbeddedGame, setShowEmbeddedGame] = useState(false);
  const iframeSrc = `${GAME_URL}?juno=1`;

  useEffect(() => {
    if (!open) return;
    setMessage(launchMessage || "The game should open in a separate window.");
  }, [open, launchMessage]);

  useEffect(() => {
    if (!open) {
      setShowEmbeddedGame(false);
      setIframeFailed(false);
    }
  }, [open]);

  if (!open) return null;

  function openPopupWindow() {
    const openedPopup = openFitnessGameWindow();
    setMessage(
      openedPopup
        ? "Game opened in a separate popup window."
        : "A new game tab was requested because the browser may have blocked the popup."
    );
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4 py-6 backdrop-blur-xl">
      <div className="glass-card relative flex max-h-[94vh] w-full max-w-4xl flex-col overflow-hidden rounded-[2rem] text-slate-100">
        <div className="relative z-10 flex flex-wrap items-center justify-between gap-3 border-b border-white/10 p-5">
          <div>
            <p className="section-kicker text-xs font-semibold">Destressing Game</p>
            <h2 className="mt-1 text-2xl font-black text-white">Play Destressing Game</h2>
            <p className="mt-1 text-sm text-slate-300/75">{message}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={openPopupWindow} className="btn-secondary px-4 py-2 text-sm font-semibold" type="button">
              Open / Reopen Game
            </button>
            <button
              onClick={() => setShowEmbeddedGame((current) => !current)}
              className="btn-secondary px-4 py-2 text-sm font-semibold"
              type="button"
            >
              {showEmbeddedGame ? "Hide Embedded View" : "Try Embedded View"}
            </button>
            <button onClick={onClose} className="btn-secondary px-4 py-2 text-sm font-semibold" type="button">
              Close
            </button>
          </div>
        </div>

        <div className="relative z-10 min-h-0 flex-1 p-5">
          <div className="min-h-[420px] overflow-hidden rounded-[1.5rem] border border-white/15 bg-slate-950/55">
            {showEmbeddedGame && !iframeFailed ? (
              <iframe
                title="Camera-based destressing game"
                src={iframeSrc}
                className="h-full min-h-[520px] w-full"
                allow="clipboard-read; clipboard-write; fullscreen; autoplay"
                // Keep this sandboxed so if the third-party site tries frame-busting
                // navigation, it cannot replace the dashboard page with motions.games.
                sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-same-origin"
                loading="lazy"
                onError={() => setIframeFailed(true)}
              />
            ) : (
              <div className="flex h-full min-h-[420px] flex-col items-center justify-center p-8 text-center">
                <p className="text-xl font-bold text-white">
                  {iframeFailed ? "Embedded game could not load." : "Game opened outside the dashboard."}
                </p>
                <p className="mt-2 max-w-lg text-sm leading-6 text-slate-300/75">
                  Some third-party sites block iframe embedding or attempt to navigate the parent page. JUNO therefore opens the game in a separate popup/tab first.
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-3">
                  <button onClick={openPopupWindow} className="btn-primary px-5 py-2.5 text-sm font-semibold" type="button">
                    Open / Reopen Game
                  </button>
                  <button
                    onClick={() => {
                      setIframeFailed(false);
                      setShowEmbeddedGame(true);
                    }}
                    className="btn-secondary px-5 py-2.5 text-sm font-semibold"
                    type="button"
                  >
                    Try Embedded View
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
