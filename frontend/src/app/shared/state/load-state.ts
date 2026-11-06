import { Signal, computed, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { Observable, Subject, catchError, concat, map, of, startWith, switchMap } from 'rxjs';

export type LoadState<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; data: T };

export type RetryableLoadSignal<T> = Signal<LoadState<T>> & { retry(): void };

export function toLoadState<T>(source: Observable<T>): Observable<LoadState<T>> {
  return source.pipe(
    map((data): LoadState<T> => ({ status: 'success', data })),
    startWith<LoadState<T>>({ status: 'loading' }),
    catchError((error: unknown) =>
      of<LoadState<T>>({
        status: 'error',
        message: error instanceof Error ? error.message : 'Erro inesperado.',
      }),
    ),
  );
}

/** Refaz a consulta sempre que `params` muda; exige contexto de injeção. */
export function loadOnChange<P, T>(
  params: Signal<P>,
  fetch: (params: P) => Observable<T>,
): RetryableLoadSignal<T> {
  const refresh = signal(0);
  const query = computed(() => ({ params: params(), refresh: refresh() }));
  const state = toSignal(toObservable(query).pipe(switchMap(({ params: current }) => toLoadState(fetch(current)))), {
    initialValue: { status: 'loading' } as LoadState<T>,
  });
  return Object.assign(state, { retry: () => refresh.update((value) => value + 1) });
}

export function loadOnce<T>(fetch: () => Observable<T>): RetryableLoadSignal<T> {
  const retries = new Subject<void>();
  const state = toSignal(concat(toLoadState(fetch()), retries.pipe(switchMap(() => toLoadState(fetch())))), {
    initialValue: { status: 'loading' } as LoadState<T>,
  });
  return Object.assign(state, { retry: () => retries.next() });
}
