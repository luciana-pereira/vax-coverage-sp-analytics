import { Signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { Observable, catchError, map, of, startWith, switchMap } from 'rxjs';

export type LoadState<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; data: T };

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
): Signal<LoadState<T>> {
  return toSignal(toObservable(params).pipe(switchMap((p) => toLoadState(fetch(p)))), {
    initialValue: { status: 'loading' } as LoadState<T>,
  });
}

export function loadOnce<T>(fetch: () => Observable<T>): Signal<LoadState<T>> {
  return toSignal(toLoadState(fetch()), { initialValue: { status: 'loading' } as LoadState<T> });
}
