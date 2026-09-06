import { useEffect, useState } from "react";

import { getAlert } from "../api";
import { C, fmtNum, fmtTime, relTime } from "../theme";
import { Dot, Label, Empty, Panel } from "./ui";

const FILTERS = [
  { key: "all", label: "all" },
  { key: "active", label: "active" },
  { key: "resolved", label: "resolved" },
];

function SnapshotGrid({ snapshot }) {
  if (!snapshot) return <Empty>loading snapshot…</Empty>;
  const t = snapshot.traffic || {};
  const rows = [
    ["orders_errors_60s", fmtNum(snapshot.orders_errors_60s)],
    ["notification_batch_p95_ms", fmtNum(snapshot.notification_batch_p95_ms, 1)],
    ["notification_batch_samples", fmtNum(snapshot.notification_batch_samples)],
    ["open_db_connections_total", fmtNum(snapshot.open_db_connections_total)],
    ["open_db_connections_peak", fmtNum(snapshot.open_db_connections_peak)],
    ["open_db_connections_rising", String(snapshot.open_db_connections_rising)],
    ["requests_per_sec", fmtNum(t.requests_per_sec, 2)],
    ["errors_per_sec", fmtNum(t.errors_per_sec, 2)],
    ["error_ratio", fmtNum((t.error_ratio || 0) * 100, 1) + "%"],
    ["p50_ms / p95_ms / p99_ms", `${fmtNum(t.p50_ms, 1)} / ${fmtNum(t.p95_ms, 1)} / ${fmtNum(t.p99_ms, 1)}`],
  ];

  const toggles = Object.entries(snapshot.bug_toggles || {});
  const connSeries = snapshot.open_db_connections_series || [];

  return (
    <div className="grid grid-cols-1 gap-x-8 gap-y-4 lg:grid-cols-2">
      <div>
        <Label>metric snapshot at fire time</Label>
        <dl className="mt-2 divide-y divide-ink-600 border-t border-ink-600">
          {rows.map(([k, v]) => (
            <div key={k} className="flex items-baseline justify-between gap-4 py-1">
              <dt className="num text-[11px] text-ink-400 truncate">{k}</dt>
              <dd className="num text-[11px] text-ink-100 shrink-0">{v}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="flex flex-col gap-4">
        <div>
          <Label>bug toggles at fire time</Label>
          <ul className="mt-2 divide-y divide-ink-600 border-t border-ink-600">
            {toggles.map(([k, on]) => (
              <li key={k} className="flex items-center justify-between gap-4 py-1">
                <span className="num text-[11px] text-ink-400 truncate">{k}</span>
                <span className="num text-[11px]" style={{ color: on ? C.status : C.muted }}>
                  {on ? "enabled" : "disabled"}
                </span>
              </li>
            ))}
          </ul>
        </div>
        {connSeries.length > 0 && (
          <div>
            <Label>open connection window</Label>
            <p className="num mt-2 text-[11px] leading-5 text-ink-300 break-words">
              [{connSeries.join(", ")}]
            </p>
          </div>
        )}
        {snapshot.recent_batches?.length > 0 && (
          <div>
            <Label>recent batches</Label>
            <ul className="num mt-2 text-[11px] leading-5 text-ink-300">
              {snapshot.recent_batches.map((b, i) => (
                <li key={i}>
                  size {b.batch_size} → {fmtNum(b.duration_ms, 1)} ms
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function AlertRow({ alert, expanded, onToggle }) {
  const [detail, setDetail] = useState(null);
  const active = alert.status === "active";

  useEffect(() => {
    if (!expanded || detail) return;
    let alive = true;
    getAlert(alert.alert_id)
      .then((d) => alive && setDetail(d))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [expanded, detail, alert.alert_id]);

  return (
    <li className="border-b border-ink-600 last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        className="grid w-full grid-cols-[16px_78px_1fr_130px_150px_74px] items-center gap-3 px-3 py-2 text-left hover:bg-ink-800"
      >
        <Dot tone={active ? "alert" : "idle"} filled={active} />
        <span
          className="num text-[10px] uppercase tracking-wider"
          style={{ color: active ? C.status : C.muted }}
        >
          {alert.severity}
        </span>
        <span className="min-w-0 truncate text-[12px] text-ink-100">
          {alert.title}
          <span className="num ml-2 text-[10px] text-ink-400">{alert.issue_type}</span>
        </span>
        <span className="num text-[11px]" style={{ color: active ? C.status : C.secondary }}>
          {fmtNum(alert.current_value, 1)}
          <span className="text-ink-400"> / {fmtNum(alert.threshold)}</span>
        </span>
        <span className="num text-[11px] text-ink-400">
          {fmtTime(alert.triggered_at)} · {relTime(alert.triggered_at)}
        </span>
        <span className="num text-[10px] uppercase tracking-wider" style={{ color: active ? C.status : C.muted }}>
          {alert.status}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-ink-600 bg-ink-900 px-3 py-3">
          <p className="mb-3 max-w-3xl text-[11px] leading-5 text-ink-300">{alert.description}</p>
          <div className="mb-4 grid grid-cols-2 gap-x-8 gap-y-1 md:grid-cols-4">
            {[
              ["alert_id", alert.alert_id],
              ["service", alert.service],
              ["metric", alert.metric_name],
              ["window", alert.window],
              ["triggered_at", fmtTime(alert.triggered_at)],
              ["resolved_at", fmtTime(alert.resolved_at)],
              ["peak", `${fmtNum(alert.peak_value, 1)} ${alert.unit}`],
              ["threshold", `${fmtNum(alert.threshold)} ${alert.unit}`],
            ].map(([k, v]) => (
              <div key={k} className="min-w-0">
                <Label>{k}</Label>
                <div className="num truncate text-[11px] text-ink-100">{v}</div>
              </div>
            ))}
          </div>
          <SnapshotGrid snapshot={detail?.snapshot} />
        </div>
      )}
    </li>
  );
}

export function AlertsPanel({ alerts, counts }) {
  const [filter, setFilter] = useState("all");
  const [openId, setOpenId] = useState(null);

  const rows = alerts.filter((a) => filter === "all" || a.status === filter);

  return (
    <div className="p-2">
      <Panel
        title="Alert log"
        right={
          <div className="flex items-center gap-3">
            <span className="num text-[10px] text-ink-400">
              {counts.active} active · {counts.resolved} resolved
            </span>
            <div className="flex items-center border border-ink-600">
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => setFilter(f.key)}
                  className="num h-5 px-2 text-[10px] border-r border-ink-600 last:border-r-0"
                  style={{
                    color: filter === f.key ? C.accent : C.muted,
                    background: filter === f.key ? "rgba(61,154,232,0.10)" : "transparent",
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        }
      >
        {rows.length === 0 ? (
          <Empty>
            {alerts.length === 0
              ? "no alerts fired — all rules within threshold"
              : `no ${filter} alerts`}
          </Empty>
        ) : (
          <ul>
            {rows.map((a) => (
              <AlertRow
                key={a.alert_id}
                alert={a}
                expanded={openId === a.alert_id}
                onToggle={() => setOpenId(openId === a.alert_id ? null : a.alert_id)}
              />
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
