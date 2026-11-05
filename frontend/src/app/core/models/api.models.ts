/** Contratos da API (espelham os schemas do OpenAPI em /openapi.json). */

export type DataStatus = 'ok' | 'data_unavailable';
export type DeficitClass = 'baixo' | 'moderado' | 'alto';

export interface CoverageSummary {
  records: number;
  municipalities: number;
  mean_coverage: number | null;
  mean_deficit: number | null;
  municipalities_below_target: number;
  critical_municipalities: number;
}

export interface DeficitDistributionItem {
  deficit_class: string;
  count: number;
}

export interface MunicipalityRankingItem {
  municipality_code: string;
  municipality_name: string | null;
  mean_coverage: number | null;
  mean_deficit: number | null;
}

export interface CoverageResponse {
  status: DataStatus;
  message: string | null;
  summary: CoverageSummary | null;
  deficit_distribution: DeficitDistributionItem[];
  top_deficit_municipalities: MunicipalityRankingItem[];
}

export interface CoverageFilterOptions {
  status: DataStatus;
  message: string | null;
  years: number[];
  immunizers: string[];
  deficit_classes: string[];
}

export interface CoverageHistoryPoint {
  year: number;
  mean_coverage: number | null;
  mean_deficit: number | null;
  records: number;
}

export interface CoverageHistorySeries {
  key: string;
  label: string;
  points: CoverageHistoryPoint[];
}

export interface CoverageHistoryResponse {
  status: DataStatus;
  message: string | null;
  series: CoverageHistorySeries[];
}

export interface MunicipalityItem {
  municipality_code: string;
  municipality_name: string | null;
  mean_coverage: number | null;
  mean_deficit: number | null;
  deficit_class: string | null;
  records: number;
}

export interface MunicipalityListResponse {
  status: DataStatus;
  message: string | null;
  total: number;
  limit: number;
  offset: number;
  items: MunicipalityItem[];
}

export interface ImmunizerSummary {
  immunizer: string;
  mean_coverage: number | null;
  mean_deficit: number | null;
}

export interface MunicipalityDetailResponse {
  municipality: MunicipalityItem;
  history: CoverageHistoryPoint[];
  by_immunizer: ImmunizerSummary[];
}

export interface PredictionItem {
  municipality_code: string;
  municipality_name: string | null;
  immunizer: string | null;
  source_year: number;
  predicted_class: string;
  probabilities: Record<string, number> | null;
}

export interface PredictionResponse {
  status: 'ok' | 'model_unavailable' | 'data_unavailable';
  message: string | null;
  model_name: string | null;
  source_year: number | null;
  target_year: number | null;
  total: number;
  class_distribution: Record<string, number>;
  items: PredictionItem[];
}

export interface ModelMetrics {
  accuracy: number;
  precision_macro: number;
  precision_weighted: number;
  recall_macro: number;
  recall_weighted: number;
  f1_macro: number;
  f1_weighted: number;
  confusion_matrix: number[][];
}

export interface ModelEntry {
  name: string;
  is_best: boolean;
  validation: ModelMetrics | null;
  test: ModelMetrics;
}

export interface SplitInfo {
  scheme: string;
  train_years: number[];
  validation_year: number | null;
  test_year: number;
  n_train: number;
  n_validation: number;
  n_test: number;
}

export interface SelectionInfo {
  criterion: string;
  split: string;
  note: string | null;
}

export interface BaselineInfo {
  description: string;
  test: ModelMetrics;
}

export interface FeatureImportanceItem {
  feature: string;
  importance: number;
}

export interface ModelResponse {
  status: 'ok' | 'not_trained';
  message: string | null;
  generated_at: string | null;
  target: string | null;
  features: string[];
  classes: string[];
  split: SplitInfo | null;
  selection: SelectionInfo | null;
  best_model: string | null;
  models: ModelEntry[];
  baseline: BaselineInfo | null;
  feature_importance: FeatureImportanceItem[];
}

export interface ArtifactStatus {
  name: string;
  description: string;
  path: string;
  exists: boolean;
  size_bytes: number | null;
}

export interface ColumnQuality {
  name: string;
  null_count: number;
  null_ratio: number;
}

export interface DatasetQuality {
  rows: number;
  municipalities: number | null;
  year_min: number | null;
  year_max: number | null;
  duplicate_rows: number;
  missing_columns: string[];
  columns: ColumnQuality[];
}

export interface DataQualityResponse {
  status: DataStatus;
  artifacts: ArtifactStatus[];
  dataset: DatasetQuality | null;
  known_gaps: string[];
}

export interface GeoFeature {
  type: 'Feature';
  properties: Record<string, unknown> | null;
  geometry: unknown;
}

export interface GeoFeatureCollection {
  type: 'FeatureCollection';
  features: GeoFeature[];
}

export interface GeoResponse {
  status: DataStatus;
  message: string | null;
  code_property: string | null;
  feature_count: number;
  geojson: GeoFeatureCollection | null;
}

/** Filtros comuns aos endpoints de cobertura/municípios. */
export interface CoverageFilters {
  year?: number | null;
  year_from?: number | null;
  year_to?: number | null;
  immunizer?: string | null;
  deficit_class?: string | null;
  municipality_code?: string[];
}
