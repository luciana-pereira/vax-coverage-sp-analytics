import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { provideRouter } from '@angular/router';
import {
    MunicipalityListResponse,
} from '../../core/models/api.models';
import {
    CoverageService,
    MunicipalitiesService,
} from '../../core/services/api.services';
import { FilterStore } from '../../core/state/filter-store.service';
import { MunicipalitiesPage } from './municipalities.page';

describe('MunicipalitiesPage', () => {
    let api!: jasmine.SpyObj<MunicipalitiesService>;
    let coverageApi!: jasmine.SpyObj<CoverageService>;

    function createResponse(
        overrides: Partial<MunicipalityListResponse> = {},
    ): MunicipalityListResponse {
        return {
            status: 'ok',
            message: null,
            total: 30,
            limit: 25,
            offset: 0,
            items: [
                {
                    municipality_code: '3550308',
                    municipality_name: 'São Paulo',
                    mean_coverage: 85,
                    mean_deficit: 15,
                    deficit_class: 'moderado',
                    records: 10,
                },
            ],
            ...overrides,
        };
    }

    beforeEach(() => {
        api = jasmine.createSpyObj<MunicipalitiesService>(
            'MunicipalitiesService',
            ['list'],
        );

        coverageApi = jasmine.createSpyObj<CoverageService>(
            'CoverageService',
            ['filters'],
        );

        api.list.and.returnValue(of(createResponse()));

        coverageApi.filters.and.returnValue(
            of({
                status: 'ok',
                message: null,
                years: [2020, 2021, 2022, 2023, 2024],
                immunizers: ['BCG', 'COVID-19'],
                deficit_classes: ['baixo', 'moderado', 'alto'],
            }),
        );

        TestBed.configureTestingModule({
            imports: [MunicipalitiesPage],
            providers: [
                { provide: MunicipalitiesService, useValue: api },
                { provide: CoverageService, useValue: coverageApi },
                provideRouter([]),
            ],
        });
    });

    it('renders municipality data', () => {
        const fixture = TestBed.createComponent(MunicipalitiesPage);
        fixture.detectChanges();

        const text = fixture.nativeElement.textContent;

        expect(text).toContain('São Paulo');
        expect(text).toContain('3550308');
        expect(text).toContain('85');
        expect(text).toContain('15');
        expect(api.list).toHaveBeenCalledWith(
            {
                year: null,
                immunizer: null,
                deficit_class: null,
            },
            25,
            0,
        );
    });

    it('moves to the next page using an offset of 25', () => {
        api.list.and.returnValue(of(createResponse()));

        const fixture = TestBed.createComponent(MunicipalitiesPage);
        fixture.detectChanges();

        const next = fixture.nativeElement.querySelectorAll(
            '.pager button',
        )[1] as HTMLButtonElement;

        next.click();
        fixture.detectChanges();

        expect(api.list).toHaveBeenCalledWith(
            {
                year: null,
                immunizer: null,
                deficit_class: null,
            },
            25,
            25,
        );
    });

    it('does not move before the first page', () => {
        const fixture = TestBed.createComponent(MunicipalitiesPage);
        fixture.detectChanges();

        const previous = fixture.nativeElement.querySelector(
            '.pager button',
        ) as HTMLButtonElement;

        expect(previous.disabled).toBeTrue();

        previous.click();
        fixture.detectChanges();

        expect(api.list).toHaveBeenCalledTimes(1);
    });

    it('resets to the first page when filters change', () => {
        const fixture = TestBed.createComponent(MunicipalitiesPage);
        fixture.detectChanges();

        const next = fixture.nativeElement.querySelectorAll(
            '.pager button',
        )[1] as HTMLButtonElement;

        next.click();
        fixture.detectChanges();

        const store = TestBed.inject(FilterStore);
        store.immunizer.set('BCG');

        fixture.detectChanges();

        expect(api.list).toHaveBeenCalledWith(
            {
                year: null,
                immunizer: 'BCG',
                deficit_class: null,
            },
            25,
            0,
        );
    });

    it('shows unavailable state when the API reports unavailable data', () => {
        api.list.and.returnValue(
            of(
                createResponse({
                    status: 'data_unavailable',
                    message: 'Dados indisponíveis.',
                    items: [],
                }),
            ),
        );

        const fixture = TestBed.createComponent(MunicipalitiesPage);
        fixture.detectChanges();

        expect(fixture.nativeElement.textContent).toContain(
            'Dados indisponíveis.',
        );
    });

    it('shows empty state when there are no municipalities', () => {
        api.list.and.returnValue(
            of(
                createResponse({
                    total: 0,
                    items: [],
                }),
            ),
        );

        const fixture = TestBed.createComponent(MunicipalitiesPage);
        fixture.detectChanges();

        expect(fixture.nativeElement.textContent).toContain(
            'Nenhum município para os filtros.',
        );
    });
});