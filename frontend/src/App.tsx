import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import CanvasEditor from "./components/CanvasEditor";
import FurniturePanel from "./components/FurniturePanel";
import type { Project, Drawing, ParseResult, PlacementAreaDTO, FurnitureType, PlacementItem } from "./types";

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [newProjectName, setNewProjectName] = useState("");

  const [drawing, setDrawing] = useState<Drawing | null>(null);
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [scaleMmPerUnit, setScaleMmPerUnit] = useState(1);

  const [areaPoints, setAreaPoints] = useState<[number, number][]>([]);
  const [holes, setHoles] = useState<[number, number][][]>([]);
  const [currentHole, setCurrentHole] = useState<[number, number][]>([]);
  const [mode, setMode] = useState<"idle" | "draw-area" | "draw-hole" | "add-item">("idle");
  const [confirmedArea, setConfirmedArea] = useState<PlacementAreaDTO | null>(null);

  const [furnitureTypes, setFurnitureTypes] = useState<FurnitureType[]>([]);
  const [placementItems, setPlacementItems] = useState<PlacementItem[]>([]);
  const [addItemTypeId, setAddItemTypeId] = useState<number | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [notesDraft, setNotesDraft] = useState("");

  const stageRef = useRef<any>(null);

  useEffect(() => {
    api.listProjects().then(setProjects);
  }, []);

  const selectProject = async (p: Project) => {
    setProject(p);
    setDrawing(null);
    setParseResult(null);
    setAreaPoints([]);
    setHoles([]);
    setCurrentHole([]);
    setMode("idle");
    setConfirmedArea(null);
    setPlacementItems([]);
    setSelectedItemId(null);
    setFurnitureTypes(await api.listFurniture(p.id));
  };

  const createProject = async () => {
    if (!newProjectName) return;
    const p = await api.createProject(newProjectName);
    setNewProjectName("");
    setProjects((prev) => [...prev, p]);
    await selectProject(p);
  };

  const handleUpload = async (file: File) => {
    if (!project) return;
    const { drawing, parse_result } = await api.uploadDrawing(project.id, file);
    setDrawing(drawing);
    setParseResult(parse_result);
    setScaleMmPerUnit(drawing.scale_mm_per_unit);
    setAreaPoints([]);
    setHoles([]);
    setCurrentHole([]);
    setMode("idle");
    setConfirmedArea(null);
    setPlacementItems([]);
    setSelectedItemId(null);
  };

  const isRaster = drawing?.file_type === "pdf" || drawing?.file_type === "image";

  const confirmArea = async () => {
    if (!project || areaPoints.length < 3) return;
    const area = await api.createArea(project.id, areaPoints, drawing?.id ?? null, holes);
    setConfirmedArea(area);
    setMode("idle");
  };

  const finishHole = () => {
    if (currentHole.length < 3) return;
    setHoles((prev) => [...prev, currentHole]);
    setCurrentHole([]);
    setMode("idle");
  };

  const removeHole = (index: number) => {
    setHoles((prev) => prev.filter((_, i) => i !== index));
  };

  const applyScale = async () => {
    if (!project || !drawing) return;
    const updated = await api.setDrawingScale(project.id, drawing.id, scaleMmPerUnit);
    setDrawing(updated);
  };

  const addFurnitureType = async (item: Omit<FurnitureType, "id" | "project_id">) => {
    if (!project) return;
    const created = await api.createFurniture(project.id, item);
    setFurnitureTypes((prev) => [...prev, created]);
  };

  const addRule = async (furnitureTypeId: number, quantity: number, minSpacingMm: number, allowRotation: boolean) => {
    if (!project || !confirmedArea) return;
    await api.createRule(project.id, {
      area_id: confirmedArea.id,
      furniture_type_id: furnitureTypeId,
      quantity,
      min_spacing_mm: minSpacingMm,
      allow_rotation: allowRotation,
    });
  };

  const runPlacement = async () => {
    if (!project || !confirmedArea) return;
    const items = await api.runPlacement(project.id, confirmedArea.id);
    setPlacementItems(items);
  };

  const onItemChange = async (id: number, x_mm: number, y_mm: number, rotation_deg: number) => {
    if (!project) return;
    setPlacementItems((prev) =>
      prev.map((it) => (it.id === id ? { ...it, x_mm, y_mm, rotation_deg, source: "manual" } : it))
    );
    await api.updatePlacementItem(project.id, id, { x_mm, y_mm, rotation_deg });
  };

  const onAddItemClick = async (x_mm: number, y_mm: number) => {
    if (!project || !confirmedArea || addItemTypeId == null) return;
    const created = await api.createPlacementItem(project.id, {
      area_id: confirmedArea.id,
      furniture_type_id: addItemTypeId,
      x_mm,
      y_mm,
    });
    setPlacementItems((prev) => [...prev, created]);
  };

  const onItemTypeChange = async (id: number, furniture_type_id: number) => {
    if (!project) return;
    setPlacementItems((prev) =>
      prev.map((it) => (it.id === id ? { ...it, furniture_type_id, source: "manual" } : it))
    );
    await api.updatePlacementItem(project.id, id, { furniture_type_id });
  };

  const onItemNotesSave = async () => {
    if (!project || selectedItemId == null) return;
    setPlacementItems((prev) =>
      prev.map((it) => (it.id === selectedItemId ? { ...it, notes: notesDraft, source: "manual" } : it))
    );
    await api.updatePlacementItem(project.id, selectedItemId, { notes: notesDraft });
  };

  const onItemDelete = async (id: number) => {
    if (!project) return;
    setPlacementItems((prev) => prev.filter((it) => it.id !== id));
    setSelectedItemId(null);
    await api.deletePlacementItem(project.id, id);
  };

  const selectedItem = placementItems.find((it) => it.id === selectedItemId) ?? null;

  useEffect(() => {
    setNotesDraft(selectedItem?.notes ?? "");
  }, [selectedItemId]);

  const exportPng = () => {
    if (!stageRef.current) return;
    const uri = stageRef.current.toDataURL({ pixelRatio: 2 });
    const link = document.createElement("a");
    link.download = `${project?.name ?? "layout"}.png`;
    link.href = uri;
    link.click();
  };

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "sans-serif" }}>
      <div style={{ width: 320, padding: 16, overflowY: "auto", borderRight: "1px solid #ddd" }}>
        <h2>도면 배치 자동화</h2>

        <div style={{ marginBottom: 16 }}>
          <h4>프로젝트</h4>
          <select
            value={project?.id ?? ""}
            onChange={(e) => {
              const p = projects.find((pp) => pp.id === Number(e.target.value));
              if (p) selectProject(p);
            }}
          >
            <option value="">선택...</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
            <input
              placeholder="새 프로젝트 이름"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
            />
            <button onClick={createProject}>생성</button>
          </div>
        </div>

        {project && (
          <>
            <div style={{ marginBottom: 16 }}>
              <h4>도면 업로드 (DXF / DWG / PDF / 이미지)</h4>
              <input
                type="file"
                accept=".dxf,.dwg,.pdf,.png,.jpg,.jpeg"
                onChange={(e) => e.target.files && handleUpload(e.target.files[0])}
              />
              {isRaster && (
                <div style={{ marginTop: 6, fontSize: 13, color: "#555" }}>
                  이미지/PDF는 실제 축척 정보가 없습니다. 도면 단위 1당 실제 mm 값을 입력하세요.
                  <div style={{ display: "flex", gap: 4, marginTop: 4 }}>
                    <input
                      type="number"
                      value={scaleMmPerUnit}
                      onChange={(e) => setScaleMmPerUnit(Number(e.target.value))}
                      style={{ width: 80 }}
                    />
                    <button onClick={applyScale}>적용</button>
                  </div>
                </div>
              )}
            </div>

            {drawing && (
              <div style={{ marginBottom: 16 }}>
                <h4>배치 영역</h4>
                <p style={{ fontSize: 13, color: "#555" }}>
                  점선으로 표시된 자동 인식 후보 영역을 클릭해 선택하거나, 아래 버튼으로 직접 그리세요.
                  빨간 점을 드래그해 경계를 보정할 수 있습니다.
                </p>
                <button
                  onClick={() => {
                    setAreaPoints([]);
                    setMode("draw-area");
                  }}
                >
                  새 영역 직접 그리기 {mode === "draw-area" ? "(캔버스 클릭으로 점 추가 중)" : ""}
                </button>{" "}
                <button onClick={confirmArea} disabled={areaPoints.length < 3}>
                  영역 확정
                </button>
                {confirmedArea && <p style={{ color: "green", fontSize: 13 }}>영역 확정됨: {confirmedArea.name}</p>}

                <div style={{ marginTop: 10, borderTop: "1px dashed #ccc", paddingTop: 8 }}>
                  <p style={{ fontSize: 13, color: "#555", margin: "0 0 4px" }}>
                    기구를 배치하면 안 되는 제외구역(데드존)을 필요한 만큼 추가할 수 있습니다. 예: 안쪽 전체를 하나의
                    제외구역으로 지정하면 바깥 테두리만 둘러 배치됩니다.
                  </p>
                  {mode !== "draw-hole" ? (
                    <button
                      onClick={() => {
                        setCurrentHole([]);
                        setMode("draw-hole");
                      }}
                    >
                      새 제외구역 그리기
                    </button>
                  ) : (
                    <button onClick={finishHole} disabled={currentHole.length < 3}>
                      제외구역 완료 ({currentHole.length}점, 캔버스 클릭으로 점 추가 중)
                    </button>
                  )}
                  {holes.length > 0 && (
                    <ul style={{ fontSize: 13, paddingLeft: 18 }}>
                      {holes.map((h, i) => (
                        <li key={i}>
                          제외구역 {i + 1} ({h.length}점){" "}
                          <button onClick={() => removeHole(i)}>삭제</button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}

            <FurniturePanel
              furnitureTypes={furnitureTypes}
              onAddFurnitureType={addFurnitureType}
              onAddRule={addRule}
              disabled={!confirmedArea}
            />

            <div style={{ marginTop: 16, borderTop: "1px solid #ddd", paddingTop: 8 }}>
              <h4 style={{ margin: "4px 0" }}>한 자리만 수동으로 추가</h4>
              <p style={{ fontSize: 13, color: "#555", margin: "0 0 4px" }}>
                판매자 개별 정보를 다 관리하지 않아도, 특정 자리에 다른 기구(예: 행거)를 놓거나 메모(전기 많이
                씀, 전자기기 있음 등)만 남기고 싶을 때 사용하세요.
              </p>
              <select
                value={addItemTypeId ?? ""}
                onChange={(e) => setAddItemTypeId(Number(e.target.value) || null)}
                disabled={!confirmedArea}
              >
                <option value="">기구 종류 선택...</option>
                {furnitureTypes.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </select>{" "}
              <button
                disabled={!confirmedArea || addItemTypeId == null}
                onClick={() => setMode(mode === "add-item" ? "idle" : "add-item")}
              >
                {mode === "add-item" ? "캔버스 클릭으로 배치 중 (끄기)" : "캔버스에 배치하기"}
              </button>
            </div>

            {selectedItem && (
              <div style={{ marginTop: 16, borderTop: "1px solid #ddd", paddingTop: 8 }}>
                <h4 style={{ margin: "4px 0" }}>선택된 자리</h4>
                <label style={{ fontSize: 13 }}>기구 종류</label>
                <select
                  value={selectedItem.furniture_type_id}
                  onChange={(e) => onItemTypeChange(selectedItem.id, Number(e.target.value))}
                  style={{ display: "block", marginBottom: 6 }}
                >
                  {furnitureTypes.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
                <label style={{ fontSize: 13 }}>특기사항 메모</label>
                <textarea
                  value={notesDraft}
                  onChange={(e) => setNotesDraft(e.target.value)}
                  placeholder="예: 전기 많이 씀, 아이스크림 기계 있음"
                  rows={3}
                  style={{ display: "block", width: "100%", boxSizing: "border-box", marginBottom: 6 }}
                />
                <button onClick={onItemNotesSave}>메모 저장</button>{" "}
                <button onClick={() => onItemDelete(selectedItem.id)}>이 자리 삭제</button>
              </div>
            )}

            <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 6 }}>
              <button onClick={runPlacement} disabled={!confirmedArea}>
                자동배치 실행 (수동으로 추가/수정한 자리는 보존됩니다)
              </button>
              <button onClick={exportPng} disabled={!drawing}>
                PNG로 내보내기
              </button>
            </div>
          </>
        )}
      </div>

      <div style={{ flex: 1, padding: 16, overflow: "auto" }}>
        <CanvasEditor
          parseResult={parseResult}
          isRaster={!!isRaster}
          imageUrl={drawing && isRaster ? api.drawingFileUrl(project!.id, drawing.id) : null}
          scaleMmPerUnit={scaleMmPerUnit}
          areaPoints={areaPoints}
          onAreaPointsChange={setAreaPoints}
          holes={holes}
          currentHole={currentHole}
          onCurrentHoleChange={setCurrentHole}
          mode={mode}
          onCandidatePick={(points) => {
            setAreaPoints(points);
            setMode("idle");
          }}
          onAddItemClick={onAddItemClick}
          furnitureTypes={furnitureTypes}
          placementItems={placementItems}
          onItemChange={onItemChange}
          selectedItemId={selectedItemId}
          onSelectItem={setSelectedItemId}
          stageRef={stageRef}
        />
      </div>
    </div>
  );
}
