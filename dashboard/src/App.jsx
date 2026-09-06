import { useCallback, useMemo, useState } from "react";

import { getAlerts, getIssues, getTimeseries } from "./api";
import { usePoll, useTicker } from "./hooks";
import { C, relTime } from "./theme";
import { Dot, Label } from "./components/ui";
import { Overview } from "./components/Overview";
import { AlertsPanel } from "./components/AlertsPanel";
import { OpsConsole } from "./components/OpsConsole";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "alerts", label: "Alerts" },
  { key: "console", label: "Console" },
];

const POLL_MS = 3000;

export default function App() {
  const [tab, setTab] = useState("overview");
  useTicker(1000);

  const ts = usePoll(() => getTimeseries(180), POLL_MS);
  const al = usePoll(() => getAlerts(100), POLL_MS);
  const hi = usePoll(getIssues, POLL_MS);

  const refreshAll = useCallback(
    () => Promise.all([ts.refresh(), al.refresh(), hi.refresh()]),
    [ts.refresh, al.refresh, hi.refresh]
  );

  const series = ts.data?.series || [];
  const thresholds = ts.data?.thresholds || {};
  const alerts = al.data?.alerts || [];
  const counts = al.data?.counts || { active: 0, resolved: 0, total: 0 };
  const issues = hi.data?.issues || [];

  const connected = !ts.error && !al.error && !hi.error;
  const lastSample = series.length ? series[series.length - 1] : null;

  const headline = useMemo(() => {
    const enabled = issues.filter((i) => i.bug_enabled).length;
    return { enabled, active: counts.active };
  }, [issues, counts.active]);

  return (
    <div className="flex min-h-full flex-col bg-ink-900">
      <header className="flex h-11 shrink-0 items-center justify-between gap-4 border-b border-ink-600 bg-ink-850 px-3">
        <div className="flex items-center gap-5 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-[13px] tracking-[0.2em] text-ink-100">ORBIT</span>
            <span className="num text-[10px] text-ink-400">observability</span>
          </div>
          <nav className="flex items-center border border-ink-600">
            {TABS.map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className="h-6 border-r border-ink-600 px-3 text-[11px] last:border-r-0"
                style={{
                  color: tab === t.key ? C.accent : C.muted,
                  background: tab === t.key ? "rgba(61,154,232,0.10)" : "transparent",
                }}
              >
                {t.label}
                {t.key === "alerts" && counts.active > 0 && (
                  <span className="num ml-1.5 text-[10px]" style={{ color: C.status }}>
                    {counts.active}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-5 shrink-0">
          <div className="flex items-center gap-1.5">
            <Dot tone={headline.active > 0 ? "alert" : "idle"} filled={headline.active > 0} />
            <span className="num text-[11px]" style={{ color: headline.active > 0 ? C.status : C.muted }}>
              {headline.active} active
            </span>
          </div>
          <span className="num text-[11px] text-ink-400">{headline.enabled}/3 bugs on</span>
          <div className="flex items-center gap-1.5">
            <Dot tone={connected ? "ok" : "alert"} filled={connected} />
            <Label>
              {connected
                ? `polling ${POLL_MS / 1000}s${lastSample ? ` · ${relTime(new Date(lastSample.t).toISOString())}` : ""}`
                : "backend unreachable"}
            </Label>
          </div>
        </div>
      </header>

      <main className="flex-1 min-w-0">
        {!hi.loaded && !ts.loaded ? (
          <div className="flex h-64 items-center justify-center text-[11px] text-ink-400">
            connecting to orbit…
          </div>
        ) : tab === "overview" ? (
          <Overview
            issues={issues}
            series={series}
            thresholds={thresholds}
            onSelectIssue={() => setTab("alerts")}
          />
        ) : tab === "alerts" ? (
          <AlertsPanel alerts={alerts} counts={counts} />
        ) : (
          <OpsConsole issues={issues} onMutated={refreshAll} />
        )}
      </main>
    </div>
  );
}
