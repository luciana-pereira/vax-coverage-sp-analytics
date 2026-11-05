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

const BASE_OPTIONS = { plugins: { legend: { position: 'bottom' } } };

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
