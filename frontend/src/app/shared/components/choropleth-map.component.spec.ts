import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GeoResponse, MunicipalityItem } from '../../core/models/api.models';
import { ChoroplethMapComponent } from './choropleth-map.component';

// Polígonos mínimos, apenas para testar a renderização (não representam municípios reais).
const GEO: GeoResponse = {
  status: 'ok',
  message: null,
  code_property: 'code',
  feature_count: 2,
  geojson: {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: { code: '1' },
        geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]] },
      },
      {
        type: 'Feature',
        properties: { code: '2' },
        geometry: { type: 'Polygon', coordinates: [[[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]] },
      },
    ],
  },
};

const ITEM: MunicipalityItem = {
  municipality_code: '1',
  municipality_name: 'Alpha',
  mean_coverage: 70,
  mean_deficit: 25,
  deficit_class: 'alto',
  records: 1,
};

describe('ChoroplethMapComponent', () => {
  let fixture: ComponentFixture<ChoroplethMapComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [ChoroplethMapComponent] });
    fixture = TestBed.createComponent(ChoroplethMapComponent);
  });

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('shows the unavailable state instead of inventing geometries', () => {
    fixture.componentRef.setInput('geo', {
      status: 'data_unavailable',
      message: 'GeoJSON municipal indisponível.',
      code_property: null,
      feature_count: 0,
      geojson: null,
    } satisfies GeoResponse);
    fixture.detectChanges();

    expect(text()).toContain('Dados indisponíveis');
    expect(fixture.nativeElement.querySelector('svg')).toBeNull();
  });

  it('renders one shape per feature colored by risk class', () => {
    fixture.componentRef.setInput('geo', GEO);
    fixture.componentRef.setInput('items', [ITEM]);
    fixture.detectChanges();

    const shapes = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<SVGPathElement>('path.map__shape'),
    );
    expect(shapes.length).toBe(2);
    expect(shapes[0].getAttribute('fill')).toBe('#c62828');
    expect(shapes[1].getAttribute('fill')).toBe('#d0d5dd');
    expect(shapes[0].textContent).toContain('Alpha');
  });

  it('emits the municipality code on click', () => {
    fixture.componentRef.setInput('geo', GEO);
    fixture.componentRef.setInput('items', [ITEM]);
    const emitted: string[] = [];
    fixture.componentInstance.selectMunicipality.subscribe((code) => emitted.push(code));
    fixture.detectChanges();

    (fixture.nativeElement as HTMLElement).querySelector<SVGPathElement>('path.map__shape')!.dispatchEvent(new Event('click'));
    expect(emitted).toEqual(['1']);
  });

  it('warns when the code property is not configured', () => {
    fixture.componentRef.setInput('geo', {
      ...GEO,
      code_property: null,
      message: 'GEOJSON_CODE_PROPERTY não configurada.',
    });
    fixture.detectChanges();
    expect(text()).toContain('GEOJSON_CODE_PROPERTY');
  });
});
