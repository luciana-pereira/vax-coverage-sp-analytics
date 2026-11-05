import { Component, computed, input, output } from '@angular/core';
import { GeoPermissibleObjects, geoMercator, geoPath } from 'd3-geo';

import { GeoResponse, MunicipalityItem } from '../../core/models/api.models';
import {
  NO_DATA_COLOR,
  RISK_COLORS,
  RISK_LABELS,
  formatPercent,
  formatPoints,
  riskColor,
  sequentialColor,
} from '../utils/format';
import { StatePanelComponent } from './state-panel.component';

export type MapMetric = 'risk' | 'coverage' | 'deficit';

interface MapShape {
  path: string;
  code: string | null;
  fill: string;
  title: string;
}

const WIDTH = 800;
const HEIGHT = 520;

/** Coroplético municipal: só desenha geometrias fornecidas pela API (GeoJSON). */
@Component({
  selector: 'app-choropleth-map',
  standalone: true,
  imports: [StatePanelComponent],
  template: `
    @if (geo() === null) {
      <app-state-panel kind="loading" />
    } @else if (geo()!.status !== 'ok' || !geo()!.geojson) {
      <app-state-panel kind="unavailable" [message]="geo()!.message">
        <p>
          O mapa depende de um GeoJSON municipal de São Paulo (variável
          <code>GEOJSON_PATH</code>); nenhuma geometria é simulada.
        </p>
      </app-state-panel>
    } @else if (!geo()!.code_property) {
      <app-state-panel kind="unavailable" [message]="geo()!.message" />
    } @else {
      <svg
        class="map"
        [attr.viewBox]="'0 0 ' + width + ' ' + height"
        role="img"
        aria-label="Mapa dos municípios de São Paulo"
      >
        @for (shape of shapes(); track $index) {
          <path
            [attr.d]="shape.path"
            [attr.fill]="shape.fill"
            [class.map__shape--selected]="shape.code !== null && shape.code === selected()"
            class="map__shape"
            tabindex="0"
            (click)="pick(shape.code)"
            (keydown.enter)="pick(shape.code)"
          >
            <title>{{ shape.title }}</title>
          </path>
        }
      </svg>
      <ul class="legend" aria-label="Legenda">
        @if (metric() === 'risk') {
          @for (entry of riskLegend; track entry.key) {
            <li><span class="legend__swatch" [style.background]="entry.color"></span>{{ entry.label }}</li>
          }
        } @else {
          <li>
            <span class="legend__swatch" [style.background]="lowColor"></span>menor
            <span class="legend__swatch" [style.background]="highColor"></span>maior
          </li>
        }
        <li><span class="legend__swatch" [style.background]="noData"></span>sem dados</li>
      </ul>
    }
  `,
})
export class ChoroplethMapComponent {
  readonly geo = input<GeoResponse | null>(null);
  readonly items = input<MunicipalityItem[]>([]);
  readonly metric = input<MapMetric>('risk');
  readonly selected = input<string | null>(null);
  readonly selectMunicipality = output<string>();

  protected readonly width = WIDTH;
  protected readonly height = HEIGHT;
  protected readonly noData = NO_DATA_COLOR;
  protected readonly lowColor = sequentialColor(0, 0, 1);
  protected readonly highColor = sequentialColor(1, 0, 1);
  protected readonly riskLegend = Object.keys(RISK_COLORS).map((key) => ({
    key,
    color: RISK_COLORS[key],
    label: RISK_LABELS[key],
  }));

  protected readonly shapes = computed<MapShape[]>(() => {
    const geo = this.geo();
    if (!geo?.geojson || !geo.code_property) return [];
    const collection = geo.geojson as unknown as GeoPermissibleObjects;
    const projection = geoMercator().fitSize([WIDTH, HEIGHT], collection);
    const toPath = geoPath(projection);

    const byCode = new Map(this.items().map((item) => [item.municipality_code, item]));
    const values = this.items()
      .map((i) => (this.metric() === 'coverage' ? i.mean_coverage : i.mean_deficit))
      .filter((v): v is number => v !== null);
    const min = values.length ? Math.min(...values) : 0;
    const max = values.length ? Math.max(...values) : 1;

    return geo.geojson.features.flatMap((feature) => {
      const path = toPath(feature as unknown as GeoPermissibleObjects);
      if (!path) return [];
      const raw = feature.properties?.[geo.code_property!];
      const code = raw === undefined || raw === null ? null : String(raw);
      const item = code ? byCode.get(code) : undefined;
      return [{ path, code, fill: this.fill(item, min, max), title: this.describe(code, item) }];
    });
  });

  protected pick(code: string | null): void {
    if (code) this.selectMunicipality.emit(code);
  }

  private fill(item: MunicipalityItem | undefined, min: number, max: number): string {
    if (!item) return NO_DATA_COLOR;
    switch (this.metric()) {
      case 'risk':
        return riskColor(item.deficit_class);
      case 'coverage':
        return sequentialColor(item.mean_coverage, min, max);
      default:
        return sequentialColor(item.mean_deficit, min, max);
    }
  }

  private describe(code: string | null, item: MunicipalityItem | undefined): string {
    if (!item) return `${code ?? 'sem código'}: sem dados`;
    const name = item.municipality_name ?? item.municipality_code;
    return `${name} — cobertura ${formatPercent(item.mean_coverage)}, déficit ${formatPoints(item.mean_deficit)}`;
  }
}
