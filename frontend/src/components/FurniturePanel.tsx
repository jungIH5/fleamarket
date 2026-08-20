import { useState } from "react";
import type { FurnitureType } from "../types";

interface Props {
  furnitureTypes: FurnitureType[];
  onAddFurnitureType: (item: Omit<FurnitureType, "id" | "project_id">) => void;
  onAddRule: (furnitureTypeId: number, quantity: number, minSpacingMm: number, allowRotation: boolean) => void;
  disabled: boolean;
}

export default function FurniturePanel({ furnitureTypes, onAddFurnitureType, onAddRule, disabled }: Props) {
  const [newName, setNewName] = useState("");
  const [newW, setNewW] = useState(1000);
  const [newH, setNewH] = useState(1000);
  const [newShape, setNewShape] = useState<"rect" | "circle">("rect");

  const [ruleInputs, setRuleInputs] = useState<Record<number, { qty: number; spacing: number; rotate: boolean }>>({});

  const ruleFor = (id: number) => ruleInputs[id] ?? { qty: 1, spacing: 300, rotate: true };
  const setRuleFor = (id: number, patch: Partial<{ qty: number; spacing: number; rotate: boolean }>) =>
    setRuleInputs((prev) => ({ ...prev, [id]: { ...ruleFor(id), ...patch } }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div>
        <h3 style={{ margin: "4px 0" }}>기구 카탈로그</h3>
        {furnitureTypes.map((f) => {
          const r = ruleFor(f.id);
          return (
            <div key={f.id} style={{ border: "1px solid #ddd", borderRadius: 6, padding: 8, marginBottom: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 12, height: 12, background: f.color, display: "inline-block", borderRadius: 3 }} />
                <b>{f.name}</b>
                <span style={{ color: "#888", fontSize: 12 }}>
                  {f.width_mm}×{f.height_mm}mm ({f.shape === "circle" ? "원형" : "사각"})
                </span>
              </div>
              <div style={{ display: "flex", gap: 6, marginTop: 6, alignItems: "center" }}>
                <label>수량</label>
                <input
                  type="number"
                  min={0}
                  value={r.qty}
                  onChange={(e) => setRuleFor(f.id, { qty: Number(e.target.value) })}
                  style={{ width: 55 }}
                />
                <label>간격(mm)</label>
                <input
                  type="number"
                  min={0}
                  value={r.spacing}
                  onChange={(e) => setRuleFor(f.id, { spacing: Number(e.target.value) })}
                  style={{ width: 60 }}
                />
                <label>
                  <input
                    type="checkbox"
                    checked={r.rotate}
                    onChange={(e) => setRuleFor(f.id, { rotate: e.target.checked })}
                  />{" "}
                  회전허용
                </label>
              </div>
              <button
                disabled={disabled || r.qty <= 0}
                onClick={() => onAddRule(f.id, r.qty, r.spacing, r.rotate)}
                style={{ marginTop: 6 }}
              >
                이 영역에 배치 조건 추가
              </button>
            </div>
          );
        })}
      </div>

      <div style={{ borderTop: "1px solid #ddd", paddingTop: 8 }}>
        <h4 style={{ margin: "4px 0" }}>새 기구 타입 추가</h4>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <input placeholder="이름 (예: 벤치)" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <div style={{ display: "flex", gap: 6 }}>
            <input type="number" placeholder="가로(mm)" value={newW} onChange={(e) => setNewW(Number(e.target.value))} />
            <input type="number" placeholder="세로(mm)" value={newH} onChange={(e) => setNewH(Number(e.target.value))} />
          </div>
          <select value={newShape} onChange={(e) => setNewShape(e.target.value as "rect" | "circle")}>
            <option value="rect">사각형</option>
            <option value="circle">원형</option>
          </select>
          <button
            disabled={!newName}
            onClick={() => {
              onAddFurnitureType({ name: newName, width_mm: newW, height_mm: newH, shape: newShape, color: "#6ac47a" });
              setNewName("");
            }}
          >
            추가
          </button>
        </div>
      </div>
    </div>
  );
}
