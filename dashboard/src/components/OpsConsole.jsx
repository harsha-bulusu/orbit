import { useState } from "react";

import { getLoadRuns, resetAll, setBug, triggerLoad } from "../api";
import { usePoll } from "../hooks";
import { C, fmtNum, fmtTime } from "../theme";
import { Button, Dot, Label, Panel, Toggle } from "./ui";

function RunOutput({ run }) {
  if (!run) {
    return <p className="num px-3 py-2 text-[11px] text-ink-400">no run recorded this session</p>;
  }
  const color = run.status === "failed" ? C.status : run.status === "running" ? C.accent : C.secondary;
  return (
    <div className="px-3 py-2">
      <div className="num mb-1.5 flex items-center gap-2 text-[10px]">
        <Dot tone={run.status === "failed" ? "alert" : "ok"} filled={run.status === "running"} />
        <span style={{ color }}>{run.status}</span>
        <span className="text-ink-400">
          started {fmtTime(run.started_at)}
          {run.finished_at ? ` · finished ${fmtTime(run.finished_at)}` : ""}
          {run.exit_code !== null && run.exit_code !== undefined ? ` · exit ${run.exit_code}` : ""}
        </span>
      </div>
      {run.output && (
        <pre className="num max-h-40 overflow-auto whitespace-pre-wrap border-l border-ink-600 pl-2 text-[11px] leading-5 text-ink-300">
          {run.output}
        </pre>
      )}
    </div>
  );
}

function IssueControl({ issue, run, busy, onToggle, onTrigger }) {
  return (
    <div className="border-b border-ink-600 last:border-b-0">
      <div className="grid grid-cols-[1fr_auto] items-start gap-4 px-3 py-2.5">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <Dot tone={issue.active_alert_id ? "alert" : "idle"} filled={Boolean(issue.active_alert_id)} />
            <span className="truncate text-[12px] text-ink-100">{issue.title}</span>
          </div>
          <div className="num mt-1 text-[10px] text-ink-400 truncate">
            {issue.issue_type} · {issue.service} · {issue.metric_name}={" "}
            <span style={{ color: issue.breaching ? C.status : C.secondary }}>
              {issue.has_data ? fmtNum(issue.current_value, 1) : "—"}
            </span>
            <span> / {fmtNum(issue.threshold)} {issue.unit}</span>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Toggle
            on={issue.bug_enabled}
            disabled={busy}
            onChange={(next) => onToggle(issue.issue_type, next)}
            labelOn="BUG ON"
            labelOff="BUG OFF"
          />
          <Button
            onClick={() => onTrigger(issue.issue_type)}
            disabled={busy || run?.status === "running"}
            title={`Runs scripts/load_test.py for ${issue.issue_type}`}
          >
            {run?.status === "running" ? "running…" : "trigger load"}
          </Button>
        </div>
      </div>
      <RunOutput run={run} />
    </div>
  );
}

export function OpsConsole({ issues, onMutated }) {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);
  const { data: runData, refresh: refreshRuns } = usePoll(getLoadRuns, 2000);
  const runs = runData?.runs || {};

  const guard = async (fn, message) => {
    setBusy(true);
    try {
      await fn();
      setNote(message);
      await Promise.all([onMutated(), refreshRuns()]);
    } catch (e) {
      setNote(`failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-2 p-2">
      <Panel
        title="Issue controls"
        right={
          <div className="flex items-center gap-3">
            {note && <span className="num text-[10px] text-ink-400">{note}</span>}
            <Button
              tone="danger"
              disabled={busy}
              onClick={() =>
                guard(resetAll, "reset — data reseeded, connections released, alert log cleared")
              }
              title="Clears orders, reseeds products, releases leaked connections, clears alerts and metric windows"
            >
              reset
            </Button>
          </div>
        }
      >
        {issues.map((issue) => (
          <IssueControl
            key={issue.issue_type}
            issue={issue}
            run={runs[issue.issue_type]}
            busy={busy}
            onToggle={(name, next) =>
              guard(() => setBug(name, next), `${name} ${next ? "enabled" : "disabled"}`)
            }
            onTrigger={(name) => guard(() => triggerLoad(name), `load triggered for ${name}`)}
          />
        ))}
      </Panel>

      <Panel title="Notes">
        <div className="px-3 py-2.5 text-[11px] leading-5 text-ink-300">
          <p>
            <Label>trigger load</Label> runs{" "}
            <span className="num text-ink-100">python -m scripts.load_test --issue N</span> in a
            subprocess on the server, driving load back against this API.
          </p>
          <p className="mt-2">
            Disabling <span className="num text-ink-100">unmanaged_connections</span> also hands the
            leaked connections back, so the saturation gauge can fall below threshold and its alert
            auto-resolves after the configured sustained-clear period.
          </p>
          <p className="mt-2">
            <span className="num text-ink-100">reset</span> reseeds the catalog, releases
            connections, and clears both the alert log and the in-memory metric windows.
          </p>
        </div>
      </Panel>
    </div>
  );
}
