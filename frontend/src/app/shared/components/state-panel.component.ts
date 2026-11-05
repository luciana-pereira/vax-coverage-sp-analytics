import { Component, input } from '@angular/core';

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
      [attr.role]="kind() === 'error' ? 'alert' : 'status'"
    >
      <strong>{{ title() }}</strong>
      @if (message()) {
        <p>{{ message() }}</p>
      }
      <ng-content />
    </div>
  `,
})
export class StatePanelComponent {
  readonly kind = input.required<PanelKind>();
  readonly message = input<string | null>(null);

  title(): string {
    return TITLES[this.kind()];
  }
}
