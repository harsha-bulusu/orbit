import { C } from "../theme";

export function Panel({ title, right, children, className = "", bodyClass = "" }) {
  return (
    <section
      className={`border border-ink-600 bg-ink-850 flex flex-col min-w-0 ${className}`}
    >
      {(title || right) && (
        <header className="flex items-center justify-between gap-3 border-b border-ink-600 px-3 h-8 shrink-0">
          <h2 className="text-[10px] uppercase tracking-[0.13em] text-ink-400">{title}</h2>
          {right}
        </header>
      )}
      <div className={`min-w-0 ${bodyClass}`}>{children}</div>
    </section>
  );
}

/** Solid dot = active/asserted, hollow ring = resolved/idle. State is carried by
 *  fill, not by color-shouting. */
export function Dot({ tone = "idle", filled = true, className = "" }) {
  const color = tone === "alert" ? C.status : tone === "ok" ? C.accent : C.borderStrong;
  return (
    <span
      className={`inline-block h-[7px] w-[7px] rounded-full shrink-0 ${className}`}
      style={
        filled
          ? { background: color }
          : { border: `1px solid ${color}`, background: "transparent" }
      }
    />
  );
}

export function Label({ children, className = "" }) {
  return (
    <span className={`text-[10px] uppercase tracking-[0.13em] text-ink-400 ${className}`}>
      {children}
    </span>
  );
}

export function Button({ children, onClick, disabled, active, tone = "default", title }) {
  const base =
    "num h-6 px-2.5 text-[11px] border transition-colors duration-75 disabled:opacity-40 disabled:cursor-not-allowed";
  const tones = {
    default: active
      ? "border-accent text-accent bg-accent/10"
      : "border-ink-600 text-ink-300 hover:border-ink-500 hover:text-ink-100 bg-ink-800",
    danger: "border-ink-600 text-status hover:border-status-dim bg-ink-800",
  };
  return (
    <button type="button" title={title} onClick={onClick} disabled={disabled} className={`${base} ${tones[tone]}`}>
      {children}
    </button>
  );
}

/** Compact on/off switch — reads as a console control, not a consumer toggle. */
export function Toggle({ on, onChange, disabled, labelOn = "ON", labelOff = "OFF" }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      disabled={disabled}
      onClick={() => onChange(!on)}
      className="num flex items-center gap-2 text-[11px] disabled:opacity-40 disabled:cursor-not-allowed group"
    >
      <span
        className="relative h-[14px] w-[26px] border transition-colors duration-100"
        style={{
          borderColor: on ? C.status : C.border,
          background: on ? "rgba(224,87,91,0.14)" : C.surface,
        }}
      >
        <span
          className="absolute top-[2px] h-[8px] w-[8px] transition-all duration-100"
          style={{ left: on ? "14px" : "2px", background: on ? C.status : C.borderStrong }}
        />
      </span>
      <span style={{ color: on ? C.status : C.muted }}>{on ? labelOn : labelOff}</span>
    </button>
  );
}

export function Empty({ children }) {
  return (
    <div className="flex items-center justify-center px-3 py-8 text-[11px] text-ink-400">
      {children}
    </div>
  );
}
