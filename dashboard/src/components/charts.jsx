import { useMemo } from "react";
import ReactECharts from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, MarkLineComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

import { baseOption } from "../theme";

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, CanvasRenderer]);

export function TimeChart({ series, yFormatter, yName, legend = false, height = 150, yMinInterval }) {
  const option = useMemo(
    () => baseOption({ series, yFormatter, yName, legend, yMinInterval }),
    [series, yFormatter, yName, legend, yMinInterval]
  );
  return (
    <ReactECharts
      echarts={echarts}
      option={option}
      notMerge
      lazyUpdate
      style={{ height, width: "100%" }}
      opts={{ renderer: "canvas" }}
    />
  );
}

/** Inline sparkline for the status cards — too small to justify a chart engine. */
export function Sparkline({ points, color, width = 84, height = 20 }) {
  const path = useMemo(() => {
    if (!points || points.length < 2) return null;
    const max = Math.max(...points, 0);
    const min = Math.min(...points, 0);
    const span = max - min || 1;
    return points
      .map((v, i) => {
        const x = (i / (points.length - 1)) * width;
        const y = height - ((v - min) / span) * (height - 2) - 1;
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [points, width, height]);

  return (
    <svg width={width} height={height} className="shrink-0" aria-hidden="true">
      {path ? (
        <path d={path} fill="none" stroke={color} strokeWidth="1.25" strokeLinejoin="round" />
      ) : (
        <line x1="0" y1={height - 1} x2={width} y2={height - 1} stroke={color} strokeWidth="1" opacity="0.3" />
      )}
    </svg>
  );
}
