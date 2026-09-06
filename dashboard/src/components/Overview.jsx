import { useMemo } from "react";

import { C, fmtNum } from "../theme";
import { lineSeries, thresholdLine } from "../theme";
import { Panel, Label, Empty } from "./ui";
import { TimeChart } from "./charts";
import { StatusCard } from "./StatusCard";

const pick = (series, key) => series.map((s) => [s.t, s[key]]);
const tail = (series, key, n = 40) => series.slice(-n).map((s) => s[key]);

const ms = (v) => `${fmtNum(v, v >= 100 || v === 0 ? 0 : 1)}`;
const rate = (v) => fmtNum(v, v >= 10 ? 0 : 1);
const count = (v) => fmtNum(v, 0);

export function Overview({ issues, series, thresholds, onSelectIssue }) {
  const sparks = useMemo(
    () => ({
      id_race_condition: tail(series, "order_errors_per_sec"),
      notification_fake_parallel: tail(series, "batch_p95_ms"),
      unmanaged_connections: tail(series, "open_connections"),
    }),
    [series]
  );

  const trafficSeries = useMemo(
    () => [
      lineSeries({
        name: "req/s",
        data: pick(series, "requests_per_sec"),
        color: C.accent,
        area: true,
      }),
    ],
    [series]
  );

  // Errors ride the status hue because they *are* the error state — the same
  // hue is never used decoratively elsewhere.
  const errorSeries = useMemo(
    () => [
      lineSeries({ name: "all 4xx/5xx", data: pick(series, "errors_per_sec"), color: C.status, opacity: 0.4 }),
      lineSeries({ name: "POST /orders", data: pick(series, "order_errors_per_sec"), color: C.status }),
      lineSeries({
        name: "5xx",
        data: pick(series, "server_errors_per_sec"),
        color: C.status,
        dashed: true,
        opacity: 0.75,
      }),
    ],
    [series]
  );

  // p50/p95/p99 are one hue at three weights — never three hues.
  const latencySeries = useMemo(
    () => [
      lineSeries({ name: "p50", data: pick(series, "p50_ms"), color: C.accent, opacity: 0.35 }),
      lineSeries({ name: "p95", data: pick(series, "p95_ms"), color: C.accent }),
      lineSeries({ name: "p99", data: pick(series, "p99_ms"), color: C.accent, dashed: true, opacity: 0.7 }),
    ],
    [series]
  );

  const saturationSeries = useMemo(
    () => [
      {
        ...lineSeries({
          name: "open connections",
          data: pick(series, "open_connections"),
          color: C.accent,
          area: true,
        }),
        markLine: thresholdLine(thresholds.open_connections, `thr ${thresholds.open_connections}`),
      },
    ],
    [series, thresholds.open_connections]
  );

  const batchSeries = useMemo(
    () => [
      {
        ...lineSeries({ name: "batch p95", data: pick(series, "batch_p95_ms"), color: C.accent, area: true }),
        markLine: thresholdLine(thresholds.batch_p95_ms, `thr ${thresholds.batch_p95_ms}ms`),
      },
    ],
    [series, thresholds.batch_p95_ms]
  );

  if (!series.length) {
    return <Empty>waiting for first metric sample…</Empty>;
  }

  return (
    <div className="flex flex-col gap-2 p-2">
      <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
        {issues.map((issue) => (
          <StatusCard
            key={issue.issue_type}
            issue={issue}
            spark={sparks[issue.issue_type]}
            onSelect={() => onSelectIssue(issue.issue_type)}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
        <Panel
          title="Traffic"
          right={<Label>req/s · 5s avg</Label>}
          bodyClass="px-1 pt-1 pb-0.5"
        >
          <TimeChart series={trafficSeries} yFormatter={rate} yName="req/s" />
        </Panel>

        <Panel title="Errors" right={<Label>err/s · by endpoint</Label>} bodyClass="px-1 pt-1 pb-0.5">
          <TimeChart series={errorSeries} yFormatter={rate} yName="err/s" legend />
        </Panel>

        <Panel title="Latency" right={<Label>http · ms</Label>} bodyClass="px-1 pt-1 pb-0.5">
          <TimeChart series={latencySeries} yFormatter={ms} yName="ms" legend />
        </Panel>

        <Panel title="Saturation" right={<Label>open db connections</Label>} bodyClass="px-1 pt-1 pb-0.5">
          <TimeChart series={saturationSeries} yFormatter={count} yName="conns" yMinInterval={1} />
        </Panel>
      </div>

      <Panel
        title="Notification batch p95"
        right={<Label>issue 2 alert metric · ms</Label>}
        bodyClass="px-1 pt-1 pb-0.5"
      >
        <TimeChart series={batchSeries} yFormatter={ms} yName="ms" height={120} />
      </Panel>
    </div>
  );
}
