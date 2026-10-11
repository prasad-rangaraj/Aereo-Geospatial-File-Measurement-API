export interface FileInfo {
  id: string;
  filename: string;
  file_type: 'shapefile' | 'kml';
  file_size_bytes: number;
  feature_count: number;
  crs?: string;
  projected_crs?: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  bounds?: [number, number, number, number];
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface FeatureMeasurementDetail {
  area_sq_m?: number | null;
  area_hectares?: number | null;
  perimeter_m?: number | null;
  length_m?: number | null;
  length_km?: number | null;
  status: 'CALCULATED' | 'NOT_APPLICABLE' | 'UNSUPPORTED' | 'INVALID_GEOMETRY';
  note?: string | null;
}

export interface FeatureItem {
  feature_index: number;
  feature_id?: string | null;
  geometry_type: string;
  geometry?: any;
  properties: Record<string, any>;
  measurement: FeatureMeasurementDetail;
}

export interface MeasurementSummary {
  total_features: number;
  calculated_features: number;
  polygon_count: number;
  linestring_count: number;
  point_count: number;
  other_count: number;
  total_area_sq_m: number;
  total_area_hectares: number;
  total_length_m: number;
  total_length_km: number;
  projected_crs?: string;
}

export interface FileMeasurementsResponse {
  id: string;
  filename: string;
  status: string;
  source_crs?: string;
  projected_crs?: string;
  summary: MeasurementSummary;
  features: FeatureItem[];
}
