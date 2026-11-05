import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  {
    path: 'dashboard',
    title: 'Visão geral',
    loadComponent: () =>
      import('./features/dashboard/dashboard.page').then((m) => m.DashboardPage),
  },
  {
    path: 'cobertura',
    title: 'Histórico de cobertura',
    loadComponent: () => import('./features/coverage/coverage.page').then((m) => m.CoveragePage),
  },
  {
    path: 'municipios',
    title: 'Municípios',
    loadComponent: () =>
      import('./features/municipalities/municipalities.page').then((m) => m.MunicipalitiesPage),
  },
  {
    path: 'municipios/:code',
    title: 'Município',
    loadComponent: () =>
      import('./features/municipalities/municipality-detail.page').then(
        (m) => m.MunicipalityDetailPage,
      ),
  },
  {
    path: 'previsoes',
    title: 'Previsões',
    loadComponent: () =>
      import('./features/predictions/predictions.page').then((m) => m.PredictionsPage),
  },
  {
    path: 'modelos',
    title: 'Modelos',
    loadComponent: () => import('./features/models/models.page').then((m) => m.ModelsPage),
  },
  {
    path: 'qualidade-dados',
    title: 'Qualidade dos dados',
    loadComponent: () =>
      import('./features/data-quality/data-quality.page').then((m) => m.DataQualityPage),
  },
  { path: '**', redirectTo: 'dashboard' },
];
