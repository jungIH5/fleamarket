export interface Project {
  id: number;
  name: string;
  created_at: string;
}

export interface Drawing {
  id: number;
  project_id: number;
  filename: string;
  file_type: "dxf" | "dwg" | "pdf" | "image";
  storage_path: string;
  preview_image_path: string | null;
  scale_mm_per_unit: number;
}

export interface CandidateArea {
  points: [number, number][];
  area: number;
  fallback?: boolean;
}

export interface ParseResult {
  segments: [[number, number], [number, number]][];
  candidate_areas: CandidateArea[];
  bounds: [number, number, number, number];
  image_size?: [number, number];
  error?: string;
}

export interface PlacementAreaDTO {
  id: number;
  project_id: number;
  drawing_id: number | null;
  name: string;
  points: [number, number][];
  holes: [number, number][][];
  source: string;
}

export interface FurnitureType {
  id: number;
  project_id: number;
  name: string;
  width_mm: number;
  height_mm: number;
  shape: "rect" | "circle";
  color: string;
}

export interface PlacementRule {
  id: number;
  project_id: number;
  area_id: number;
  furniture_type_id: number;
  quantity: number;
  min_spacing_mm: number;
  allow_rotation: boolean;
}

export interface PlacementItem {
  id: number;
  project_id: number;
  area_id: number;
  furniture_type_id: number;
  x_mm: number;
  y_mm: number;
  rotation_deg: number;
  notes: string | null;
  source: "auto" | "manual";
}
