// The whole UI is built from three hues: a neutral slate ramp, one accent, one
// status color. Series that must be told apart vary opacity or dash pattern
// inside these — a fourth hue is never introduced.
export const C = {
  ground: "#0b0e14",
  panel: "#0e121a",
  surface: "#11151e",
  inset: "#1a1f2b",
  border: "#232a38",
  borderStrong: "#38414f",
  muted: "#6b7683",
  secondary: "#98a2b0",
  primary: "#d7dce3",
  accent: "#3d9ae8",
  accentDim: "#2a6ba3",
  status: "#e0575b",
  statusDim: "#93393c",
};

const MONO = 'ui-monospace, "SF Mono", Menlo, Consolas, monospace';

export const fmtClock = (ms) => {
  const d = new Date(ms);
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
};

export const fmtTime = (iso) => (iso ? fmtClock(new Date(iso).getTime()) : "—");

export const fmtNum = (v, digits = 0) =>
  v === null || v === undefined || Number.isNaN(v)
    ? "—"
    : Number(v).toLocaleString(undefined, {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });

export const relTime = (iso) => {
  if (!iso) return "—";
  const secs = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s ago`;
  return `${Math.floor(secs / 3600)}h ago`;
};

const axisLine = { lineStyle: { color: C.border } };

/**
 * Shared ECharts option scaffold: recessive grid and axes, monospace numerals,
 * crosshair tooltip on every chart.
 */
export function baseOption({ series, yFormatter, yName, legend, yMinInterval }) {
  return {
    animation: false,
    backgroundColor: "transparent",
    grid: { left: 46, right: 14, top: legend ? 26 : 12, bottom: 22 },
    legend: legend
      ? {
          show: true,
          top: 0,
          right: 0,
          itemWidth: 14,
          itemHeight: 2,
          itemGap: 14,
          icon: "roundRect",
          textStyle: { color: C.muted, fontSize: 10, fontFamily: MONO },
        }
      : { show: false },
    tooltip: {
      trigger: "axis",
      backgroundColor: C.surface,
      borderColor: C.border,
      borderWidth: 1,
      padding: [6, 9],
      textStyle: { color: C.primary, fontSize: 11, fontFamily: MONO },
      axisPointer: {
        type: "line",
        lineStyle: { color: C.borderStrong, width: 1, type: [3, 3] },
        label: { show: false },
      },
      formatter: (rows) => {
        const head = `<span style="color:${C.muted}">${fmtClock(rows[0].axisValue)}</span>`;
        const body = rows
          .map(
            (r) =>
              `<div style="display:flex;gap:12px;justify-content:space-between">` +
              `<span style="color:${C.secondary}">${r.marker}${r.seriesName}</span>` +
              `<span>${yFormatter(r.value[1])}</span></div>`
          )
          .join("");
        return head + body;
      },
    },
    xAxis: {
      type: "time",
      axisLine,
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: {
        color: C.muted,
        fontSize: 10,
        fontFamily: MONO,
        hideOverlap: true,
        formatter: (v) => fmtClock(v),
      },
    },
    yAxis: {
      type: "value",
      name: yName,
      nameTextStyle: { color: C.muted, fontSize: 9, align: "left", padding: [0, 0, 4, -38] },
      nameGap: 8,
      min: 0,
      // Count axes would otherwise render duplicated "0 0 1 1" fractional ticks
      // while the series sits at zero.
      minInterval: yMinInterval,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: C.border, type: [2, 4] } },
      axisLabel: { color: C.muted, fontSize: 10, fontFamily: MONO, formatter: yFormatter },
    },
    series,
  };
}

/** One line series. `emphasisLevel` controls how loud it reads within its hue. */
export function lineSeries({ name, data, color, dashed = false, opacity = 1, area = false, width = 1.6 }) {
  return {
    name,
    type: "line",
    showSymbol: false,
    symbol: "circle",
    symbolSize: 8,
    data,
    lineStyle: { color, width, opacity, type: dashed ? [5, 4] : "solid" },
    itemStyle: { color, opacity },
    areaStyle: area ? { color, opacity: 0.08 } : undefined,
    emphasis: { focus: "series" },
  };
}

/** Dashed horizontal reference line at a configured threshold. */
export function thresholdLine(value, label) {
  return {
    silent: true,
    symbol: "none",
    label: {
      show: true,
      position: "insideEndTop",
      formatter: label,
      color: C.status,
      fontSize: 9,
      fontFamily: MONO,
    },
    lineStyle: { color: C.statusDim, width: 1, type: [4, 4] },
    data: [{ yAxis: value }],
  };
}
