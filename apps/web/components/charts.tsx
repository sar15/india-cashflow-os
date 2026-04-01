"use client";

import { useEffect, useRef } from "react";
import type { ECharts, EChartsOption } from "echarts";

import type { DashboardChart, DashboardChartTracePoint } from "@/lib/dashboard-types";
import { formatCurrency } from "@/lib/formatters";

type ForecastChartProps = {
  chart: DashboardChart;
  onPointClick?: (point: DashboardChartTracePoint) => void;
};

type ChartClickParams = {
  dataIndex?: number;
};

function buildCurrencyAxisFormatter(value: unknown) {
  if (Array.isArray(value)) {
    return formatCurrency(Number(value[0] ?? 0));
  }
  if (value instanceof Date) {
    return value.toISOString().slice(0, 10);
  }
  return formatCurrency(Number(value ?? 0));
}

function buildLineAreaOption(chart: DashboardChart): EChartsOption {
  return {
    grid: { left: 18, right: 18, top: 24, bottom: 44, containLabel: true },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value) => buildCurrencyAxisFormatter(value ?? 0)
    },
    xAxis: {
      type: "category",
      data: chart.xAxis,
      axisLabel: { color: "#5f7680" },
      axisLine: { lineStyle: { color: "rgba(22, 49, 60, 0.18)" } }
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#5f7680",
        formatter: (value: number) => buildCurrencyAxisFormatter(value)
      },
      splitLine: { lineStyle: { color: "rgba(22, 49, 60, 0.08)" } }
    },
    series: chart.series.map((series) => ({
      type: "line",
      name: series.name,
      data: series.values,
      smooth: true,
      symbolSize: 8,
      lineStyle: { width: 3, color: "#0f8b8d" },
      areaStyle: {
        color: {
          type: "linear",
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: "rgba(15, 139, 141, 0.35)" },
            { offset: 1, color: "rgba(15, 139, 141, 0.04)" }
          ]
        }
      },
      itemStyle: { color: "#0f8b8d" }
    }))
  };
}

function buildGroupedBarOption(chart: DashboardChart): EChartsOption {
  return {
    grid: { left: 18, right: 18, top: 24, bottom: 44, containLabel: true },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value) => buildCurrencyAxisFormatter(value ?? 0)
    },
    legend: { bottom: 0, textStyle: { color: "#5f7680" } },
    xAxis: {
      type: "category",
      data: chart.xAxis,
      axisLabel: { color: "#5f7680" },
      axisLine: { lineStyle: { color: "rgba(22, 49, 60, 0.18)" } }
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#5f7680",
        formatter: (value: number) => buildCurrencyAxisFormatter(value)
      },
      splitLine: { lineStyle: { color: "rgba(22, 49, 60, 0.08)" } }
    },
    series: chart.series.map((series, index) => ({
      type: "bar",
      name: series.name,
      data: series.values,
      barMaxWidth: 28,
      itemStyle: {
        borderRadius: [10, 10, 0, 0],
        color: index === 0 ? "#0f8b8d" : "#f07167"
      }
    }))
  };
}

function buildWaterfallOption(chart: DashboardChart): EChartsOption {
  const values = chart.series[0]?.values ?? [];
  return {
    grid: { left: 18, right: 18, top: 24, bottom: 44, containLabel: true },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value) => buildCurrencyAxisFormatter(value ?? 0)
    },
    xAxis: {
      type: "category",
      data: chart.xAxis,
      axisLabel: { color: "#5f7680" },
      axisLine: { lineStyle: { color: "rgba(22, 49, 60, 0.18)" } }
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#5f7680",
        formatter: (value: number) => buildCurrencyAxisFormatter(value)
      },
      splitLine: { lineStyle: { color: "rgba(22, 49, 60, 0.08)" } }
    },
    series: [
      {
        type: "bar",
        data: values.map((value, index) => ({
          value,
          itemStyle: {
            color: index === 1 ? "#f07167" : "#0f8b8d",
            borderRadius: 12
          }
        })),
        barMaxWidth: 56,
        label: {
          show: true,
          position: "top",
          color: "#16313c",
          formatter: (params: { value?: unknown }) => formatCurrency(Number(params.value ?? 0))
        }
      }
    ]
  };
}

function buildHeatmapOption(chart: DashboardChart): EChartsOption {
  const values = chart.series[0]?.values ?? [];
  const max = Math.max(...values, 1);

  return {
    grid: { left: 18, right: 18, top: 24, bottom: 44, containLabel: true },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value) => buildCurrencyAxisFormatter(value ?? 0)
    },
    xAxis: {
      type: "category",
      data: chart.xAxis,
      axisLabel: { color: "#5f7680" },
      axisLine: { lineStyle: { color: "rgba(22, 49, 60, 0.18)" } }
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#5f7680",
        formatter: (value: number) => buildCurrencyAxisFormatter(value)
      },
      splitLine: { show: false }
    },
    series: [
      {
        type: "bar",
        data: values.map((value) => ({
          value,
          itemStyle: {
            color: `rgba(15, 139, 141, ${Math.max(value / max, 0.1)})`,
            borderRadius: [12, 12, 0, 0]
          }
        })),
        barMaxWidth: 42
      }
    ]
  };
}

function buildTimelineOption(chart: DashboardChart): EChartsOption {
  return {
    grid: { left: 18, right: 18, top: 24, bottom: 56, containLabel: true },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value) => buildCurrencyAxisFormatter(value ?? 0)
    },
    xAxis: {
      type: "category",
      data: chart.xAxis,
      axisLabel: { color: "#5f7680", rotate: 22 },
      axisLine: { lineStyle: { color: "rgba(22, 49, 60, 0.18)" } }
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#5f7680",
        formatter: (value: number) => buildCurrencyAxisFormatter(value)
      },
      splitLine: { lineStyle: { color: "rgba(22, 49, 60, 0.08)" } }
    },
    series: chart.series.map((series) => ({
      type: "bar",
      name: series.name,
      data: series.values,
      itemStyle: {
        color: "#d4a373",
        borderRadius: [10, 10, 0, 0]
      },
      barMaxWidth: 34
    }))
  };
}

function buildParetoOption(chart: DashboardChart): EChartsOption {
  const values = chart.series[0]?.values ?? [];
  const total = values.reduce((sum, value) => sum + value, 0) || 1;
  let runningTotal = 0;
  const cumulative = values.map((value) => {
    runningTotal += value;
    return Number(((runningTotal / total) * 100).toFixed(1));
  });

  return {
    grid: { left: 18, right: 42, top: 24, bottom: 56, containLabel: true },
    tooltip: {
      trigger: "axis"
    },
    legend: { bottom: 0, textStyle: { color: "#5f7680" } },
    xAxis: {
      type: "category",
      data: chart.xAxis,
      axisLabel: { color: "#5f7680", rotate: 18 },
      axisLine: { lineStyle: { color: "rgba(22, 49, 60, 0.18)" } }
    },
    yAxis: [
      {
        type: "value",
        axisLabel: {
          color: "#5f7680",
          formatter: (value: number) => buildCurrencyAxisFormatter(value)
        },
        splitLine: { lineStyle: { color: "rgba(22, 49, 60, 0.08)" } }
      },
      {
        type: "value",
        min: 0,
        max: 100,
        axisLabel: {
          color: "#5f7680",
          formatter: (value: number) => `${value}%`
        },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        type: "bar",
        name: chart.series[0]?.name ?? "Amount",
        data: values,
        barMaxWidth: 36,
        itemStyle: {
          color: "#0f8b8d",
          borderRadius: [10, 10, 0, 0]
        }
      },
      {
        type: "line",
        name: "Cumulative %",
        yAxisIndex: 1,
        data: cumulative,
        smooth: true,
        symbolSize: 8,
        itemStyle: { color: "#f07167" },
        lineStyle: { color: "#f07167", width: 2.5 }
      }
    ]
  };
}

function buildScenarioOption(chart: DashboardChart): EChartsOption {
  return {
    grid: { left: 18, right: 18, top: 24, bottom: 44, containLabel: true },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value) => buildCurrencyAxisFormatter(value ?? 0)
    },
    legend: { bottom: 0, textStyle: { color: "#5f7680" } },
    xAxis: {
      type: "category",
      data: chart.xAxis,
      axisLabel: { color: "#5f7680" },
      axisLine: { lineStyle: { color: "rgba(22, 49, 60, 0.18)" } }
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#5f7680",
        formatter: (value: number) => buildCurrencyAxisFormatter(value)
      },
      splitLine: { lineStyle: { color: "rgba(22, 49, 60, 0.08)" } }
    },
    series: chart.series.map((series, index) => ({
      type: series.kind === "line" ? "line" : "bar",
      name: series.name,
      data: series.values,
      smooth: series.kind === "line",
      symbolSize: 8,
      barMaxWidth: 40,
      itemStyle: {
        color: index === 0 ? "#0f8b8d" : "#f07167",
        borderRadius: series.kind === "line" ? 0 : [10, 10, 0, 0]
      },
      lineStyle: {
        width: series.kind === "line" ? 2.5 : undefined,
        color: index === 0 ? "#0f8b8d" : "#f07167"
      }
    }))
  };
}

function buildChartOption(chart: DashboardChart): EChartsOption {
  switch (chart.kind) {
    case "line-area":
      return buildLineAreaOption(chart);
    case "stacked-bars":
      return buildGroupedBarOption(chart);
    case "waterfall":
      return buildWaterfallOption(chart);
    case "heatmap":
      return buildHeatmapOption(chart);
    case "timeline":
      return buildTimelineOption(chart);
    case "pareto":
      return buildParetoOption(chart);
    case "scenario":
      return buildScenarioOption(chart);
    default:
      return buildGroupedBarOption(chart);
  }
}

export function ForecastChart({ chart, onPointClick }: Readonly<ForecastChartProps>) {
  const chartRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    let chartInstance: ECharts | undefined;
    let resizeObserver: ResizeObserver | undefined;

    async function mountChart() {
      const echarts = await import("echarts");
      if (!active || !chartRef.current) {
        return;
      }

      chartInstance =
        echarts.getInstanceByDom(chartRef.current) ??
        echarts.init(chartRef.current, undefined, { renderer: "svg" });
      chartInstance.setOption(buildChartOption(chart), true);

      if (onPointClick && chart.tracePoints.length > 0) {
        const handleClick = (params: ChartClickParams) => {
          const point = typeof params.dataIndex === "number" ? chart.tracePoints[params.dataIndex] : undefined;
          if (point) {
            onPointClick(point);
          }
        };
        chartInstance.on("click", handleClick);
      }

      resizeObserver = new ResizeObserver(() => {
        chartInstance?.resize();
      });
      resizeObserver.observe(chartRef.current);
    }

    void mountChart();

    return () => {
      active = false;
      resizeObserver?.disconnect();
      chartInstance?.dispose();
    };
  }, [chart, onPointClick]);

  const interactive = Boolean(onPointClick && chart.tracePoints.length > 0);

  return (
    <div
      ref={chartRef}
      className={`chart-surface${interactive ? " interactive" : ""}`}
      role="img"
      aria-label={chart.title}
    />
  );
}
