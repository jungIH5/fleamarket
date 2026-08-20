import { useMemo, useRef, useEffect } from "react";
import { Stage, Layer, Line, Circle, Rect, Text, Image as KonvaImage, Transformer, Group } from "react-konva";
import useImage from "use-image";
import type { ParseResult, FurnitureType, PlacementItem } from "../types";

const CANVAS_W = 900;
const CANVAS_H = 620;

interface Props {
  parseResult: ParseResult | null;
  isRaster: boolean;
  imageUrl: string | null;
  scaleMmPerUnit: number;
  areaPoints: [number, number][]; // 원본 도면 좌표계(drawing unit) 기준
  onAreaPointsChange: (points: [number, number][]) => void;
  holes: [number, number][][]; // 확정된 제외구역 목록
  currentHole: [number, number][]; // 편집 중인 제외구역
  onCurrentHoleChange: (points: [number, number][]) => void;
  mode: "idle" | "draw-area" | "draw-hole" | "add-item";
  onCandidatePick: (points: [number, number][]) => void;
  onAddItemClick: (x_mm: number, y_mm: number) => void;
  furnitureTypes: FurnitureType[];
  placementItems: PlacementItem[];
  onItemChange: (id: number, x_mm: number, y_mm: number, rotation_deg: number) => void;
  selectedItemId: number | null;
  onSelectItem: (id: number | null) => void;
  stageRef?: React.RefObject<any>;
}

export default function CanvasEditor({
  parseResult,
  isRaster,
  imageUrl,
  scaleMmPerUnit,
  areaPoints,
  onAreaPointsChange,
  holes,
  currentHole,
  onCurrentHoleChange,
  mode,
  onCandidatePick,
  onAddItemClick,
  furnitureTypes,
  placementItems,
  onItemChange,
  selectedItemId,
  onSelectItem,
  stageRef,
}: Props) {
  const [image] = useImage(imageUrl || "", "anonymous");
  const shapeRefs = useRef<Record<number, any>>({});
  const trRef = useRef<any>(null);

  const bounds = parseResult?.bounds ?? [0, 0, 1000, 1000];
  const boundsMm = useMemo(
    () => [bounds[0] * scaleMmPerUnit, bounds[1] * scaleMmPerUnit, bounds[2] * scaleMmPerUnit, bounds[3] * scaleMmPerUnit],
    [bounds, scaleMmPerUnit]
  );
  const widthMm = Math.max(1, boundsMm[2] - boundsMm[0]);
  const heightMm = Math.max(1, boundsMm[3] - boundsMm[1]);
  const pxPerMm = Math.min((CANVAS_W - 40) / widthMm, (CANVAS_H - 40) / heightMm);

  const toPx = (xMm: number, yMm: number): [number, number] => [
    20 + (xMm - boundsMm[0]) * pxPerMm,
    20 + (boundsMm[3] - yMm) * pxPerMm,
  ];
  const toMmFromPx = (xPx: number, yPx: number): [number, number] => [
    (xPx - 20) / pxPerMm + boundsMm[0],
    boundsMm[3] - (yPx - 20) / pxPerMm,
  ];
  const rawToPx = (p: [number, number]) => toPx(p[0] * scaleMmPerUnit, p[1] * scaleMmPerUnit);
  const pxToRaw = (xPx: number, yPx: number): [number, number] => {
    const [xMm, yMm] = toMmFromPx(xPx, yPx);
    return [xMm / scaleMmPerUnit, yMm / scaleMmPerUnit];
  };

  useEffect(() => {
    if (selectedItemId != null && trRef.current && shapeRefs.current[selectedItemId]) {
      trRef.current.nodes([shapeRefs.current[selectedItemId]]);
      trRef.current.getLayer().batchDraw();
    } else if (trRef.current) {
      trRef.current.nodes([]);
    }
  }, [selectedItemId, placementItems]);

  const handleStageClick = (e: any) => {
    if (mode === "idle") {
      if (e.target === e.target.getStage()) onSelectItem(null);
      return;
    }
    const pos = e.target.getStage().getPointerPosition();
    if (mode === "add-item") {
      const [xMm, yMm] = toMmFromPx(pos.x, pos.y);
      onAddItemClick(xMm, yMm);
      return;
    }
    const raw = pxToRaw(pos.x, pos.y);
    if (mode === "draw-area") {
      onAreaPointsChange([...areaPoints, raw]);
    } else {
      onCurrentHoleChange([...currentHole, raw]);
    }
  };

  const areaFlat = areaPoints.flatMap((p) => rawToPx(p));
  const currentHoleFlat = currentHole.flatMap((p) => rawToPx(p));

  return (
    <Stage
      ref={stageRef}
      width={CANVAS_W}
      height={CANVAS_H}
      style={{ background: "#fff", border: "1px solid #ccc" }}
      onClick={handleStageClick}
    >
      <Layer>
        {isRaster && image && (
          <KonvaImage
            image={image}
            x={20}
            y={20}
            width={widthMm * pxPerMm}
            height={heightMm * pxPerMm}
            opacity={0.85}
          />
        )}

        {!isRaster &&
          parseResult?.segments.map((seg, i) => {
            const p1 = toPx(seg[0][0] * scaleMmPerUnit, seg[0][1] * scaleMmPerUnit);
            const p2 = toPx(seg[1][0] * scaleMmPerUnit, seg[1][1] * scaleMmPerUnit);
            return <Line key={i} points={[...p1, ...p2]} stroke="#888" strokeWidth={1} />;
          })}

        {/* 자동 인식된 후보 영역들 (클릭해서 선택) */}
        {parseResult?.candidate_areas.map((cand, i) => (
          <Line
            key={i}
            points={cand.points.flatMap((p) => rawToPx(p as [number, number]))}
            closed
            fill="rgba(74,144,217,0.08)"
            stroke="rgba(74,144,217,0.5)"
            strokeWidth={1}
            dash={[4, 4]}
            onClick={(e) => {
              e.cancelBubble = true;
              onCandidatePick(cand.points as [number, number][]);
            }}
          />
        ))}

        {/* 확정/편집 중인 배치 영역 */}
        {areaPoints.length >= 2 && (
          <Line points={areaFlat} closed={areaPoints.length >= 3} stroke="#e04848" strokeWidth={2} fill="rgba(224,72,72,0.08)" />
        )}
        {areaPoints.map((p, i) => {
          const [px, py] = rawToPx(p);
          return (
            <Circle
              key={i}
              x={px}
              y={py}
              radius={6}
              fill="#e04848"
              draggable
              onDragMove={(e) => {
                const raw = pxToRaw(e.target.x(), e.target.y());
                const next = [...areaPoints];
                next[i] = raw;
                onAreaPointsChange(next);
              }}
            />
          );
        })}

        {/* 확정된 제외구역(데드존) - 빗금 표시 */}
        {holes.map((hole, hi) => (
          <Line
            key={`hole-${hi}`}
            points={hole.flatMap((p) => rawToPx(p))}
            closed
            fill="rgba(120,120,120,0.35)"
            stroke="#555"
            strokeWidth={2}
            dash={[6, 4]}
          />
        ))}

        {/* 편집 중인 제외구역 */}
        {currentHole.length >= 2 && (
          <Line
            points={currentHoleFlat}
            closed={currentHole.length >= 3}
            stroke="#333"
            strokeWidth={2}
            fill="rgba(120,120,120,0.25)"
            dash={[6, 4]}
          />
        )}
        {currentHole.map((p, i) => {
          const [px, py] = rawToPx(p);
          return (
            <Circle
              key={`ch-${i}`}
              x={px}
              y={py}
              radius={6}
              fill="#555"
              draggable
              onDragMove={(e) => {
                const raw = pxToRaw(e.target.x(), e.target.y());
                const next = [...currentHole];
                next[i] = raw;
                onCurrentHoleChange(next);
              }}
            />
          );
        })}

        {/* 배치된 기구 */}
        {placementItems.map((item) => {
          const ftype = furnitureTypes.find((f) => f.id === item.furniture_type_id);
          if (!ftype) return null;
          const [px, py] = toPx(item.x_mm, item.y_mm);
          const wPx = ftype.width_mm * pxPerMm;
          const hPx = ftype.height_mm * pxPerMm;
          const isManual = item.source === "manual";
          const common = {
            x: px,
            y: py,
            rotation: item.rotation_deg,
            draggable: true,
            onClick: (e: any) => {
              e.cancelBubble = true;
              onSelectItem(item.id);
            },
            onDragEnd: (e: any) => {
              const [xMm, yMm] = toMmFromPx(e.target.x(), e.target.y());
              onItemChange(item.id, xMm, yMm, e.target.rotation());
            },
            onTransformEnd: (e: any) => {
              const node = e.target;
              const [xMm, yMm] = toMmFromPx(node.x(), node.y());
              onItemChange(item.id, xMm, yMm, node.rotation());
            },
            ref: (node: any) => {
              if (node) shapeRefs.current[item.id] = node;
            },
          };
          return (
            <Group key={item.id}>
              {ftype.shape === "circle" ? (
                <Circle
                  {...common}
                  radius={wPx / 2}
                  fill={ftype.color}
                  opacity={0.85}
                  stroke={isManual ? "#c0392b" : "#333"}
                  strokeWidth={isManual ? 2 : 1}
                  dash={isManual ? [4, 3] : undefined}
                />
              ) : (
                <Rect
                  {...common}
                  width={wPx}
                  height={hPx}
                  offsetX={wPx / 2}
                  offsetY={hPx / 2}
                  fill={ftype.color}
                  opacity={0.85}
                  stroke={isManual ? "#c0392b" : "#333"}
                  strokeWidth={isManual ? 2 : 1}
                  dash={isManual ? [4, 3] : undefined}
                />
              )}
              {item.notes && (
                <>
                  <Circle x={px + wPx / 2} y={py - hPx / 2} radius={8} fill="#e04848" listening={false} />
                  <Text
                    x={px + wPx / 2 - 4}
                    y={py - hPx / 2 - 6}
                    text="!"
                    fontSize={12}
                    fontStyle="bold"
                    fill="#fff"
                    listening={false}
                  />
                </>
              )}
            </Group>
          );
        })}

        <Transformer ref={trRef} rotateEnabled resizeEnabled={false} />
      </Layer>
    </Stage>
  );
}
