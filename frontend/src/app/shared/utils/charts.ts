import { ChartConfiguration } from 'chart.js';

export interface LineSeries {
  label: string;
  data: (number | null)[];
  color: string;
}

export interface BarSeries {
  label: string;
  data: number[];
  colors: string | string[];
}

export interface ChartTableData {
  series: string[];
  rows: { label: string; values: (number | string | null)[] }[];
}

const BASE_OPTIONS = { plugins: { legend: { position: 'bottom' } } };

export function chartTable(config: ChartConfiguration): ChartTableData {
  const labels = Array.isArray(config.data.labels) ? config.data.labels.map(String) : [];
  const datasets = config.data.datasets.map((dataset, index) => {
    const raw = dataset as unknown as { label?: string; data?: unknown };
    const values = Array.isArray(raw.data)
      ? raw.data.map((value): number | string | null =>
          typeof value === 'number' || typeof value === 'string' ? value : null,
        )
      : [];
    return { label: raw.label || `Série ${index + 1}`, values };
  });

  return {
    series: datasets.map((dataset) => dataset.label),
    rows: labels.map((label, index) => ({
      label,
      values: datasets.map((dataset) => dataset.values[index] ?? null),
    })),
  };
}

export function lineChart(
  labels: (string | number)[],
  series: LineSeries[],
  yTitle: string,
): ChartConfiguration {
  return {
    type: 'line',
    data: {
      labels: labels.map(String),
      datasets: series.map((s) => ({
        label: s.label,
        data: s.data,
        borderColor: s.color,
        backgroundColor: s.color,
        tension: 0.2,
        spanGaps: true,
      })),
    },
    options: {
      ...BASE_OPTIONS,
      scales: { y: { title: { display: true, text: yTitle } } },
    },
  } as ChartConfiguration;
}

export function barChart(
  labels: string[],
  series: BarSeries[],
  options: { horizontal?: boolean; yTitle?: string; max?: number } = {},
): ChartConfiguration {
  const valueAxis = {
    beginAtZero: true,
    max: options.max,
    title: { display: !!options.yTitle, text: options.yTitle ?? '' },
  };
  return {
    type: 'bar',
    data: {
      labels,
      datasets: series.map((s) => ({
        label: s.label,
        data: s.data,
        backgroundColor: s.colors,
      })),
    },
    options: {
      ...BASE_OPTIONS,
      indexAxis: options.horizontal ? 'y' : 'x',
      scales: options.horizontal ? { x: valueAxis } : { y: valueAxis },
    },
  } as ChartConfiguration;
}

export function doughnutChart(labels: string[], data: number[], colors: string[]): ChartConfiguration {
  return {
    type: 'doughnut',
    data: { labels, datasets: [{ data, backgroundColor: colors }] },
    options: BASE_OPTIONS,
  } as ChartConfiguration;
}
