import { useEffect, useRef, useState } from "react";

const IDLE_MS = 15_000;

function idleDelayMs() {
  const raw = Number(new URLSearchParams(window.location.search).get("idle"));
  return raw > 0 ? raw * 1000 : IDLE_MS;
}

export function useIdleRaccoon(paused) {
  const [visible, setVisible] = useState(false);
  const lastRef = useRef(Date.now());

  useEffect(() => {
    if (paused) {
      setVisible(false);
      lastRef.current = Date.now();
      return undefined;
    }

    const delay = idleDelayMs();
    lastRef.current = Date.now();

    const mark = () => {
      lastRef.current = Date.now();
      setVisible(false);
    };

    const tick = () => {
      if (Date.now() - lastRef.current >= delay) {
        setVisible(true);
      }
    };

    const id = window.setInterval(tick, 400);
    window.addEventListener("click", mark, true);
    window.addEventListener("keydown", mark, true);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("click", mark, true);
      window.removeEventListener("keydown", mark, true);
    };
  }, [paused]);

  return visible;
}

function RaccoonSvg() {
  return (
    <svg viewBox="0 0 88 78" width="88" height="78" aria-hidden="true">
      <ellipse cx="22" cy="16" rx="11" ry="13" fill="#3a3a3a" />
      <ellipse cx="66" cy="16" rx="11" ry="13" fill="#3a3a3a" />
      <ellipse cx="23" cy="18" rx="5.5" ry="6.5" fill="#f8af5a" />
      <ellipse cx="65" cy="18" rx="5.5" ry="6.5" fill="#f8af5a" />
      <ellipse cx="44" cy="40" rx="30" ry="26" fill="#6a6a6a" />
      <ellipse cx="28" cy="38" rx="15" ry="11" fill="#141414" />
      <ellipse cx="60" cy="38" rx="15" ry="11" fill="#141414" />
      <ellipse cx="44" cy="50" rx="13" ry="10" fill="#f3f3f5" />
      <ellipse cx="44" cy="45" rx="5.2" ry="3.6" fill="#f04a5e" />
      <g className="critter-raccoon-eye">
        <circle cx="28" cy="38" r="4.2" fill="#fafafa" />
        <circle cx="29" cy="39" r="2.3" fill="#141414" />
        <circle cx="27.6" cy="37.4" r="0.8" fill="#fafafa" />
      </g>
      <g className="critter-raccoon-eye critter-raccoon-eye-right">
        <circle cx="60" cy="38" r="4.2" fill="#fafafa" />
        <circle cx="61" cy="39" r="2.3" fill="#141414" />
        <circle cx="59.6" cy="37.4" r="0.8" fill="#fafafa" />
      </g>
      <path
        d="M37 54q7 5 14 0"
        fill="none"
        stroke="#141414"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <ellipse cx="24" cy="72" rx="12" ry="6.5" fill="#4a4a4a" />
      <ellipse cx="64" cy="72" rx="12" ry="6.5" fill="#4a4a4a" />
      <circle cx="18" cy="71" r="1.7" fill="#f8af5a" />
      <circle cx="24" cy="70" r="1.7" fill="#f8af5a" />
      <circle cx="30" cy="71" r="1.7" fill="#f8af5a" />
      <circle cx="58" cy="71" r="1.7" fill="#f8af5a" />
      <circle cx="64" cy="70" r="1.7" fill="#f8af5a" />
      <circle cx="70" cy="71" r="1.7" fill="#f8af5a" />
    </svg>
  );
}

export function IdleRaccoon() {
  return (
    <button
      type="button"
      title="ну и долго же ты думаешь"
      aria-label="Енот выглянул. Кликни, чтобы спрятать."
      className="critter-raccoon fixed right-8 top-[4.75rem] z-[100] border-0 bg-transparent p-0 drop-shadow-md"
    >
      <span className="critter-raccoon-inner block origin-bottom">
        <RaccoonSvg />
      </span>
    </button>
  );
}
