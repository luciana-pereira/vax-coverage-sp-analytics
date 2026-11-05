import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { firstValueFrom, of, throwError, toArray } from 'rxjs';

import { loadOnChange, loadOnce, toLoadState } from './load-state';

describe('toLoadState', () => {
    it('emits loading and then success', async () => {
        const states = await firstValueFrom(toLoadState(of(42)).pipe(toArray()));
        expect(states).toEqual([{ status: 'loading' }, { status: 'success', data: 42 }]);
    });

    it('turns errors into an error state with the message', async () => {
        const states = await firstValueFrom(
            toLoadState(throwError(() => new Error('falhou'))).pipe(toArray()),
        );
        expect(states).toEqual([{ status: 'loading' }, { status: 'error', message: 'falhou' }]);
    });

    it('reruns the query when the parameters change', async () => {
        const params = signal(1);
        const fetch = jasmine.createSpy('fetch').and.callFake((value: number) => of(value * 10));

        const state = TestBed.runInInjectionContext(() => loadOnChange(params, fetch));

        expect(state()).toEqual({ status: 'loading' });

        await new Promise((resolve) => setTimeout(resolve));

        expect(fetch).toHaveBeenCalledWith(1);
        expect(state()).toEqual({ status: 'success', data: 10 });

        params.set(2);

        await new Promise((resolve) => setTimeout(resolve));

        expect(fetch).toHaveBeenCalledWith(2);
        expect(state()).toEqual({ status: 'success', data: 20 });
    });

    it('loads the data only once', () => {
        const fetch = jasmine.createSpy('fetch').and.returnValue(of(42));

        const state = TestBed.runInInjectionContext(() => loadOnce(fetch));

        expect(state()).toEqual({ status: 'success', data: 42 });
        expect(fetch).toHaveBeenCalledTimes(1);
    });
});
