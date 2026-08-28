import axios from "axios";
import type {
  Project,
  Drawing,
  ParseResult,
  PlacementAreaDTO,
  FurnitureType,
  PlacementRule,
  PlacementItem,
} from "./types";

// exe로 패키징된 빌드는 프론트/백엔드가 같은 프로세스·같은 포트에서 서빙되므로 상대경로("")를 쓴다
// (frontend/.env.production에서 VITE_API_BASE=""로 지정). Docker+Vite dev 환경에서는 백엔드가
// 별도 포트(8000)에 떠 있으므로 기본값으로 절대주소를 쓴다.
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const client = axios.create({ baseURL: API_BASE });

export const api = {
  listProjects: () => client.get<Project[]>("/projects").then((r) => r.data),
  createProject: (name: string) => client.post<Project>("/projects", { name }).then((r) => r.data),

  uploadDrawing: (projectId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return client
      .post<{ drawing: Drawing; parse_result: ParseResult }>(`/projects/${projectId}/drawings`, form)
      .then((r) => r.data);
  },
  drawingFileUrl: (projectId: number, drawingId: number) =>
    `${API_BASE}/projects/${projectId}/drawings/${drawingId}/file`,
  setDrawingScale: (projectId: number, drawingId: number, scaleMmPerUnit: number) =>
    client
      .put<Drawing>(`/projects/${projectId}/drawings/${drawingId}/scale`, null, {
        params: { scale_mm_per_unit: scaleMmPerUnit },
      })
      .then((r) => r.data),

  createArea: (
    projectId: number,
    points: [number, number][],
    drawingId: number | null,
    holes: [number, number][][] = [],
    name = "배치 영역"
  ) =>
    client
      .post<PlacementAreaDTO>(`/projects/${projectId}/areas`, {
        project_id: projectId,
        drawing_id: drawingId,
        name,
        points,
        holes,
        source: "manual",
      })
      .then((r) => r.data),
  updateArea: (
    projectId: number,
    areaId: number,
    points: [number, number][],
    name: string,
    holes: [number, number][][] = []
  ) =>
    client
      .put<PlacementAreaDTO>(`/projects/${projectId}/areas/${areaId}`, {
        project_id: projectId,
        name,
        points,
        holes,
        source: "manual",
      })
      .then((r) => r.data),
  listAreas: (projectId: number) =>
    client.get<PlacementAreaDTO[]>(`/projects/${projectId}/areas`).then((r) => r.data),

  listFurniture: (projectId: number) =>
    client.get<FurnitureType[]>(`/projects/${projectId}/furniture`).then((r) => r.data),
  createFurniture: (projectId: number, item: Omit<FurnitureType, "id" | "project_id">) =>
    client
      .post<FurnitureType>(`/projects/${projectId}/furniture`, { ...item, project_id: projectId })
      .then((r) => r.data),
  deleteFurniture: (projectId: number, furnitureId: number) =>
    client.delete(`/projects/${projectId}/furniture/${furnitureId}`),

  listRules: (projectId: number) =>
    client.get<PlacementRule[]>(`/projects/${projectId}/rules`).then((r) => r.data),
  createRule: (projectId: number, rule: Omit<PlacementRule, "id" | "project_id">) =>
    client.post<PlacementRule>(`/projects/${projectId}/rules`, { ...rule, project_id: projectId }).then((r) => r.data),
  deleteRule: (projectId: number, ruleId: number) => client.delete(`/projects/${projectId}/rules/${ruleId}`),

  runPlacement: (projectId: number, areaId: number) =>
    client.post<PlacementItem[]>(`/projects/${projectId}/placement/run/${areaId}`).then((r) => r.data),
  listPlacementItems: (projectId: number) =>
    client.get<PlacementItem[]>(`/projects/${projectId}/placement/items`).then((r) => r.data),
  createPlacementItem: (
    projectId: number,
    item: { area_id: number; furniture_type_id: number; x_mm: number; y_mm: number; rotation_deg?: number; notes?: string | null }
  ) =>
    client
      .post<PlacementItem>(`/projects/${projectId}/placement/items`, {
        project_id: projectId,
        rotation_deg: 0,
        notes: null,
        ...item,
      })
      .then((r) => r.data),
  updatePlacementItem: (
    projectId: number,
    itemId: number,
    item: Partial<Pick<PlacementItem, "x_mm" | "y_mm" | "rotation_deg" | "furniture_type_id" | "notes">>
  ) => client.put<PlacementItem>(`/projects/${projectId}/placement/items/${itemId}`, item).then((r) => r.data),
  deletePlacementItem: (projectId: number, itemId: number) =>
    client.delete(`/projects/${projectId}/placement/items/${itemId}`),
};
