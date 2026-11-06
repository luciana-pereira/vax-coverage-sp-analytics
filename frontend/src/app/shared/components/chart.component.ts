import { Component, ElementRef, OnDestroy, computed, effect, input, viewChild } from '@angular/core';
import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  ChartConfiguration,
  DoughnutController,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from 'chart.js';

import { chartTable } from '../utils/charts';

Chart.register(
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  DoughnutController,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
);

/** Envolve o Chart.js; recria o gráfico quando `config` muda. */
@Component({
  selector: 'app-chart',
  standalone: true,
  template: `
    <div class="chart-box">
      <canvas #canvas role="img" [attr.aria-label]="ariaLabel()"></canvas>
    </div>
    <details class="chart-data-table">
      <summary>Ver dados do gráfico em tabela</summary>
      @let tableData = table();
      @if (tableData.rows.length > 0) {
        <div class="table-wrap">
          <table class="table">
            <caption class="visually-hidden">{{ ariaLabel() }}</caption>
            <thead>
              <tr>
                <th scope="col">Categoria</th>
                @for (series of tableData.series; track $index) {
                  <th scope="col">{{ series }}</th>
                }
              </tr>
            </thead>
            <tbody>
              @for (row of tableData.rows; track $index) {
                <tr>
                  <th scope="row">{{ row.label }}</th>
                  @for (value of row.values; track $index) {
                    <td class="num">{{ valueText(value) }}</td>
                  }
                </tr>
              }
            </tbody>
          </table>
        </div>
      } @else {
        <p>Sem dados para exibir.</p>
      }
    </details>
  `,
})
export class ChartComponent implements OnDestroy {
  readonly config = input.required<ChartConfiguration>();
  readonly ariaLabel = input<string>('Gráfico');

  private readonly canvas = viewChild<ElementRef<HTMLCanvasElement>>('canvas');
  private chart?: Chart;
  protected readonly table = computed(() => chartTable(this.config()));

  constructor() {
    effect(() => {
      const element = this.canvas();
      const config = this.config();
      if (!element) return;
      this.chart?.destroy();
      this.chart = new Chart(element.nativeElement, {
        ...config,
        options: { responsive: true, maintainAspectRatio: false, ...config.options },
      });
    });
  }

  ngOnDestroy(): void {
    this.chart?.destroy();
  }

  protected valueText(value: number | string | null): string {
    if (value === null) return 'Sem dados';
    return typeof value === 'number'
      ? new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value)
      : value;
  }
}
