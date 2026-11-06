import { Component, input, output } from '@angular/core';

export type PanelKind = 'loading' | 'error' | 'empty' | 'unavailable';

const TITLES: Record<PanelKind, string> = {
  loading: 'Carregando…',
  error: 'Não foi possível carregar os dados',
  empty: 'Sem resultados',
  unavailable: 'Dados indisponíveis',
};

@Component({
  selector: 'app-state-panel',
  standalone: true,
  template: `
    <div
      class="state-panel"
      [class.state-panel--error]="kind() === 'error'"
      [class.state-panel--loading]="kind() === 'loading'"
      [attr.role]="kind() === 'error' ? 'alert' : 'status'"
      [attr.aria-live]="kind() === 'loading' ? 'polite' : null"
    >
      <strong>{{ title() }}</strong>
      @if (message()) {
        <p>{{ message() }}</p>
      }
      @if (retryable()) {
        <button class="btn state-panel__retry" type="button" (click)="retry.emit()">
          Tentar novamente
        </button>
      }
      <ng-content />
    </div>
  `,
})
export class StatePanelComponent {
  readonly kind = input.required<PanelKind>();
  readonly message = input<string | null>(null);
  readonly retryable = input(false);
  readonly retry = output<void>();

  title(): string {
    return TITLES[this.kind()];
  }
}
