import { Component, computed, inject, input, signal } from '@angular/core';

import {
  AnalyticsAgeGroup,
  AnalyticsMunicipalityCount,
  AnalyticsVaccineCount,
  MunicipalityBasis,
  VaccinationAnalyticsQuery,
  VaccinationAnalyticsResponse,
} from '../../core/models/api.models';
import {
  VaccinationAnalyticsService,
  VaccinationAnalyticsSession,
} from '../../core/services/api.services';
import { ChartComponent } from './chart.component';
import { StatePanelComponent } from './state-panel.component';
import { LoadState, loadOnChange } from '../state/load-state';
import { barChart, lineChart } from '../utils/charts';

export type AnalyticsPanelView = 'overview' | 'history' | 'municipalities';

@Component({
  selector: 'app-vaccination-analytics-panel',
  standalone: true,
  imports: [ChartComponent, StatePanelComponent],
  template: `
    <section class="analytics-panel" aria-label="Análises agregadas de vacinação">
      @if (view() === 'overview') {
        <section class="analytics-panel__upload" aria-labelledby="analytics-upload-title">
          <div>
            <h2 id="analytics-upload-title">Carregamento de arquivo via CSV para Análise</h2>
            <p id="analytics-upload-description">Envie arquivos de dados vacinais (.csv) para processamento e atualização dos indicadores.</p>
          </div>
          <label class="csv-upload">
            <input
              class="csv-upload__input"
              id="analytics-csv"
              type="file"
              accept=".csv,text/csv"
              aria-describedby="analytics-upload-description"
              [disabled]="uploading()"
              (change)="onUpload($event)"
            />
            <span class="csv-upload__button">
              <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 16V4m-4 4 4-4 4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
              </svg>
              Escolher arquivo CSV
            </span>
          </label>
          @if (uploading()) {
            <span role="status">Validando e agregando o CSV…</span>
          } @else if (uploadError()) {
            <span role="alert">{{ uploadError() }}</span>
          } @else if (uploadCount() !== null) {
            <span role="status">{{ uploadCount() }} linhas agregadas; conteúdo individual não foi retido.</span>
            <button type="button" class="btn" (click)="resetSource()">Voltar à fonte local</button>
          }
        </section>
      }

      <form class="filters" (submit)="$event.preventDefault()" aria-label="Filtros de vacinação">
        <div class="field">
          <label for="analytics-year">Ano</label>
          <select id="analytics-year" [value]="filters().year ?? ''" (change)="onYear($event)">
            <option value="">Mais recente</option>
            @for (year of years(); track year) {
              <option [value]="year">{{ year }}</option>
            }
          </select>
        </div>
        <div class="field">
          <label for="analytics-vaccine">Vacina</label>
          <select id="analytics-vaccine" [value]="filters().vaccine ?? ''" (change)="onVaccine($event)">
            <option value="">Todas</option>
            @for (vaccine of vaccines(); track vaccine.key) {
              <option [value]="vaccine.key">{{ vaccine.label }}</option>
            }
          </select>
        </div>
        <div class="field">
          <label for="analytics-age">Faixa etária</label>
          <select id="analytics-age" [value]="filters().age_group ?? ''" [disabled]="ageGroups().length === 0" (change)="onAge($event)">
            <option value="">Todas</option>
            @for (age of ageGroups(); track age) {
              <option [value]="age">{{ age }} anos</option>
            }
          </select>
        </div>
        <div class="field">
          <label for="analytics-basis">Município considerado</label>
          <select id="analytics-basis" [value]="filters().municipality_basis ?? 'patient'" (change)="onBasis($event)">
            <option value="patient">Código do paciente</option>
            <option value="application">Estabelecimento de aplicação</option>
          </select>
        </div>
        <div class="field">
          <label for="analytics-municipality">Município</label>
          <select id="analytics-municipality" [value]="filters().municipality_code ?? ''" [disabled]="municipalities().length === 0" (change)="onMunicipality($event)">
            <option value="">Todos</option>
            @for (municipality of municipalities(); track municipality.code) {
              <option [value]="municipality.code">{{ municipality.name ?? municipality.code }}</option>
            }
          </select>
        </div>
      </form>

      @let state = analytics();
      @if (state.status === 'loading') {
        <app-state-panel kind="loading" />
      } @else if (state.status === 'error') {
        <app-state-panel kind="error" [message]="state.message" [retryable]="true" (retry)="analytics.retry()" />
      } @else if (state.data.status !== 'ok') {
        <app-state-panel kind="unavailable" [message]="state.data.message" />
      } @else {
        @let data = state.data;
        <p class="page__lead">
          Fonte: <strong>{{ data.source }}</strong> · {{ int(data.total_doses) }} doses ·
          período {{ data.period_start ?? '—' }} a {{ data.period_end ?? '—' }} ·
          atualização {{ updatedAt(data.source_updated_at) }}.
        </p>
        @for (warning of data.warnings; track warning) {
          @if (warning === 'Driver PostgreSQL não instalado.') {
            <details class="analytics-panel__database-status">
              <summary>Banco de dados: usando fonte local</summary>
              <p>{{ warning }}</p>
            </details>
          } @else {
            <p class="analytics-panel__warning" role="status">{{ warning }}</p>
          }
        }

        @if (view() === 'overview' || view() === 'history') {
          <article class="card">
            <h2>Doses aplicadas por mês</h2>
            @if (monthlyChart(); as config) {
              <app-chart [config]="config" ariaLabel="Doses de vacinação por mês, dados agregados da fonte selecionada" />
            } @else {
              <app-state-panel kind="empty" message="Não há doses no período selecionado." />
            }
          </article>
        }

        @if (view() === 'overview') {
          <div class="grid grid--two">
            <article class="card">
              <h2>Doses por vacina</h2>
              @if (vaccineChart(); as config) {
                <app-chart [config]="config" ariaLabel="Doses agregadas por código, sigla e descrição da vacina" />
              } @else {
                <app-state-panel kind="empty" message="A fonte não informa uma dimensão de vacina utilizável." />
              }
            </article>
            <article class="card">
              <h2>Doses por sexo</h2>
              @if (!data.dimensions['sex']) {
                <app-state-panel kind="unavailable" message="A fonte selecionada não contém sexo do paciente." />
              } @else {
                @if (sexChart(); as config) {
                  <app-chart [config]="config" ariaLabel="Doses agregadas por sexo" />
                } @else {
                  <app-state-panel kind="empty" message="Sem valores de sexo para os filtros." />
                }
              }
            </article>
            <article class="card">
              <h2>Doses por faixa etária</h2>
              @if (!data.dimensions['age']) {
                <app-state-panel kind="unavailable" message="A fonte selecionada não contém idade ou data de nascimento." />
              } @else {
                @if (ageChart(); as config) {
                  <app-chart [config]="config" ariaLabel="Doses agregadas nas faixas de 0 a 4 e 60 anos ou mais" />
                } @else {
                  <app-state-panel kind="empty" message="Sem valores nas faixas de 0–4 ou 60+ para os filtros." />
                }
              }
            </article>
          </div>
        }

        @if (view() === 'municipalities') {
          <article class="card">
            <h2>Doses por município</h2>
            @if (!data.statewide) {
              <app-state-panel kind="unavailable" message="Comparação municipal bloqueada: a fonte não comprova abrangência estadual." />
            } @else if (filters().municipality_basis === 'application' && !data.dimensions['application_municipality']) {
              <app-state-panel kind="unavailable" message="A fonte não informa o município do estabelecimento de aplicação; não foi substituído pelo município do paciente." />
            } @else {
              @if (municipalityChart(); as config) {
                <p class="page__lead">{{ municipalityBasisLabel() }}. O código do paciente não é tratado como residência nem como local de aplicação.</p>
                <app-chart [config]="config" ariaLabel="Doses agregadas por município e papel geográfico selecionado" />
              } @else {
                <app-state-panel kind="empty" message="Sem municípios para os filtros selecionados." />
              }
            }
          </article>
        }
      }
    </section>
  `,
})
export class VaccinationAnalyticsPanelComponent {
  readonly view = input.required<AnalyticsPanelView>();
  private readonly api = inject(VaccinationAnalyticsService);
  private readonly session = inject(VaccinationAnalyticsSession);

  protected readonly filters = signal<VaccinationAnalyticsQuery>({ municipality_basis: 'patient' });
  private readonly query = computed(() => ({
    ...this.filters(),
    source_token: this.session.sourceToken(),
  }));
  protected readonly analytics = loadOnChange(this.query, (query) => this.api.analytics(query));
  protected readonly uploading = signal(false);
  protected readonly uploadError = signal<string | null>(null);
  protected readonly uploadCount = signal<number | null>(null);
  protected readonly int = new Intl.NumberFormat('pt-BR').format;

  protected readonly data = computed(() => {
    const state = this.analytics();
    return state.status === 'success' && state.data.status === 'ok' ? state.data : null;
  });
  protected readonly years = computed(() => this.data()?.filters.years ?? []);
  protected readonly vaccines = computed(() => this.data()?.filters.vaccines ?? []);
  protected readonly ageGroups = computed(() => this.data()?.filters.age_groups ?? []);
  protected readonly municipalities = computed(() => {
    const data = this.data();
    if (!data) return [];
    return this.filters().municipality_basis === 'application'
      ? data.filters.application_municipalities
      : data.filters.patient_municipalities;
  });

  protected readonly monthlyChart = computed(() => {
    const rows = this.data()?.monthly ?? [];
    return rows.length
      ? lineChart(
          rows.map((row) => row.month),
          [{ label: 'Doses', data: rows.map((row) => row.doses), color: '#0d9488' }],
          'Doses aplicadas',
        )
      : null;
  });

  protected readonly vaccineChart = computed(() => {
    const items = this.data()?.by_vaccine.slice(0, 20) ?? [];
    return items.length
      ? barChart(
          items.map((item) => item.label),
          [{ label: 'Doses', data: items.map((item) => item.doses), colors: '#1769f5' }],
          { horizontal: true, yTitle: 'Doses aplicadas' },
        )
      : null;
  });

  protected readonly sexChart = computed(() => this.categoryChart(this.data()?.by_sex ?? []));
  protected readonly ageChart = computed(() =>
    this.categoryChart((this.data()?.by_age_group ?? []).filter((item) => item.key === '0-4' || item.key === '60+')),
  );

  protected readonly municipalityChart = computed(() => {
    const data = this.data();
    if (!data?.statewide) return null;
    const rows: AnalyticsMunicipalityCount[] =
      this.filters().municipality_basis === 'application'
        ? data.by_application_municipality
        : data.by_patient_municipality;
    const items = rows.slice(0, 20);
    return items.length
      ? barChart(
          items.map((item) => item.name ?? item.code),
          [{ label: 'Doses', data: items.map((item) => item.doses), colors: '#c62828' }],
          { horizontal: true, yTitle: 'Doses aplicadas' },
        )
      : null;
  });

  protected onYear(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.filters.update((current) => ({ ...current, year: value ? Number(value) : null }));
  }

  protected onVaccine(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.filters.update((current) => ({ ...current, vaccine: value || null }));
  }

  protected onAge(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as AnalyticsAgeGroup | '';
    this.filters.update((current) => ({ ...current, age_group: value || null }));
  }

  protected onBasis(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as MunicipalityBasis;
    this.filters.update((current) => ({ ...current, municipality_basis: value, municipality_code: null }));
  }

  protected onMunicipality(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.filters.update((current) => ({ ...current, municipality_code: value || null }));
  }

  protected onUpload(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.uploadError.set(null);
    this.uploadCount.set(null);
    this.uploading.set(true);
    this.api.upload(file).subscribe({
      next: (response) => {
        this.uploading.set(false);
        this.uploadCount.set(response.accepted_rows);
        this.session.useSourceToken(response.source_token);
      },
      error: (error: unknown) => {
        this.uploading.set(false);
        this.uploadError.set(error instanceof Error ? error.message : 'Não foi possível validar o CSV.');
      },
    });
    (event.target as HTMLInputElement).value = '';
  }

  protected resetSource(): void {
    this.session.useSourceToken(null);
    this.uploadCount.set(null);
    this.uploadError.set(null);
  }

  protected updatedAt(value: string | null): string {
    return value ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)) : 'não informada';
  }

  protected municipalityBasisLabel(): string {
    return this.filters().municipality_basis === 'application'
      ? 'Município do estabelecimento de aplicação'
      : 'Município do paciente (não equivale automaticamente à residência)';
  }

  private categoryChart(items: VaccinationAnalyticsResponse['by_sex']) {
    return items.length
      ? barChart(
          items.map((item) => item.label),
          [{ label: 'Doses', data: items.map((item) => item.doses), colors: '#0d9488' }],
          { yTitle: 'Doses aplicadas' },
        )
      : null;
  }
}