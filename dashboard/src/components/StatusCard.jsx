import { C, fmtNum, relTime } from "../theme";
import { Dot, Label } from "./ui";
import { Sparkline } from "./charts";

export function StatusCard({ issue, spark, onSelect }) {
  const alerting = Boolean(issue.active_alert_id);
  const tone = alerting ? "alert" : issue.bug_enabled ? "idle" : "ok";
  const valueColor = alerting ? C.status : issue.has_data ? C.primary : C.muted;

  return (
    <button
      type="button"
      onClick={onSelect}
      className="group border border-ink-600 bg-ink-850 px-3 py-2.5 text-left flex flex-col gap-2.5 min-w-0 hover:border-ink-500"
      style={alerting ? { borderColor: C.statusDim } : undefined}
    >
      <div className="flex items-start justify-between gap-2 min-w-0">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <Dot tone={tone} filled={alerting} />
            <span className="text-[12px] text-ink-100 truncate">{issue.title}</span>
          </div>
          <div className="num mt-1 text-[10px] text-ink-400 truncate">{issue.service}</div>
        </div>
        <div className="num text-[10px] shrink-0" style={{ color: issue.bug_enabled ? C.status : C.muted }}>
          {issue.bug_enabled ? "BUG ON" : "BUG OFF"}
        </div>
      </div>

      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <div className="num text-[26px] leading-none" style={{ color: valueColor }}>
            {issue.has_data ? fmtNum(issue.current_value, issue.unit === "ms" ? 0 : 0) : "—"}
            <span className="ml-1 text-[11px] text-ink-400">{issue.unit}</span>
          </div>
          <div className="num mt-1.5 text-[10px] text-ink-400 truncate">
            {issue.metric_name} · thr {fmtNum(issue.threshold)} · {issue.window}
          </div>
        </div>
        <Sparkline points={spark} color={alerting ? C.status : C.accent} />
      </div>

      <div className="flex items-center gap-1.5 border-t border-ink-600 pt-2 min-w-0">
        {alerting ? (
          <>
            <Dot tone="alert" />
            <span className="num text-[10px] truncate" style={{ color: C.status }}>
              firing {relTime(issue.active_alert_since)}
            </span>
          </>
        ) : (
          <>
            <Dot tone="idle" filled={false} />
            <Label className="truncate">
              {issue.has_data ? "within threshold" : "awaiting samples"}
            </Label>
          </>
        )}
      </div>
    </button>
  );
}
