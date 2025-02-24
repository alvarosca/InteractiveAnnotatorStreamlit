import React, { useEffect, useState } from "react";
import { Layer, Stage, Image, Rect } from "react-konva";
import Point from "./Point";
import Konva from "konva";

export interface PointCanvasProps {
  pointsInfo: any[];
  mode: string;
  selectedId: string | null;
  setSelectedId: any;
  setPointsInfo: any;
  setLabel: any;
  color_map: any;
  scale: number;
  label: string;
  image_size: number[];
  image: any;
  mask: any;
  maskOpacity?: number;
  contour: any;
  contourOpacity?: number;
  strokeWidth: number;
  zoom: number;
}

const PointCanvas = (props: PointCanvasProps) => {
  const {
    pointsInfo,
    mode,
    selectedId,
    setSelectedId,
    setPointsInfo,
    setLabel,
    color_map,
    scale,
    label,
    image_size,
    image,
    mask,
    maskOpacity = 0.5,
    contour,
    contourOpacity = 1,
    strokeWidth,
    zoom,
  } = props;

  const [selectionBox, setSelectionBox] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [startPos, setStartPos] = useState<{ x: number; y: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = (e: any) => {
    if (mode !== "Transform") return;
  
    const stage = e.target.getStage();
    const pointer = stage.getPointerPosition();
    if (!pointer) return;
  
    const clickedPoint = pointsInfo.find(point => {
      const pointScreenX = point.x * scale * zoom;
      const pointScreenY = point.y * scale * zoom;
      return Math.abs(pointScreenX - pointer.x) < 5 && Math.abs(pointScreenY - pointer.y) < 5;
    });
  
    if (clickedPoint) {
      // Clicked on an existing point → Select it
      setSelectedId(clickedPoint.id);
      setLabel(clickedPoint.label);
      setSelectionBox(null);
      setStartPos(null);
      return;
    }
  
    // Start drawing selection box or placing a new point
    setStartPos({ x: pointer.x, y: pointer.y });
    setSelectionBox({ x: pointer.x, y: pointer.y, width: 0, height: 0 });
    setIsDragging(false); // Reset dragging state
  };
  
  const handleMouseMove = (e: any) => {
    if (!startPos) return;
  
    const stage = e.target.getStage();
    const pointer = stage.getPointerPosition();
    if (!pointer) return;
  
    setSelectionBox({
      x: Math.min(startPos.x, pointer.x),
      y: Math.min(startPos.y, pointer.y),
      width: Math.abs(pointer.x - startPos.x),
      height: Math.abs(pointer.y - startPos.y),
    });
  };
  
  const handleMouseUp = (e: any) => {
    if (!startPos) return;
  
    const stage = e.target.getStage();
    const pointer = stage.getPointerPosition();
    if (!pointer) return;
  
    // Compute drag distance
    const dx = pointer.x - startPos.x;
    const dy = pointer.y - startPos.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
  
    const isActuallyDragging = distance > 10; // Consider dragging if moved more than 10 pixels
  
    if (!isActuallyDragging) {
      // **Click event: Add a new point**
      const newPoint = {
        id: `${Date.now()}`,
        x: pointer.x / (scale * zoom),
        y: pointer.y / (scale * zoom),
        label: label,
        stroke: color_map[label],
      };
      setPointsInfo([...pointsInfo, newPoint]);
      setSelectedId(newPoint.id);
      setLabel(newPoint.label);
    } else {
      // **Selection logic**
      const centerX = selectionBox!.x + selectionBox!.width / 2;
      const centerY = selectionBox!.y + selectionBox!.height / 2;
  
      const xMin = selectionBox!.x / (scale * zoom);
      const yMin = selectionBox!.y / (scale * zoom);
      const xMax = (selectionBox!.x + selectionBox!.width) / (scale * zoom);
      const yMax = (selectionBox!.y + selectionBox!.height) / (scale * zoom);
  
      let closestPoint: (typeof pointsInfo)[number] | null = null;
      let minDist = Infinity;
  
      pointsInfo.forEach((point) => {
        if (point.x >= xMin && point.x <= xMax && point.y >= yMin && point.y <= yMax) {
          const pointScreenX = point.x * scale * zoom;
          const pointScreenY = point.y * scale * zoom;
          const dist = Math.sqrt((centerX - pointScreenX) ** 2 + (centerY - pointScreenY) ** 2);
  
          if (dist < minDist) {
            minDist = dist;
            closestPoint = point;
          }
        }
      });
  
      if (closestPoint) {
        setSelectedId(closestPoint.id);
        setLabel(closestPoint.label);
      } else {
        setSelectedId(null);
      }
    }
  
    setSelectionBox(null);
    setStartPos(null);
    setIsDragging(false);
  };
  

  return (
    <div>
      <Stage
        width={image_size[0] * (scale * zoom)}
        height={image_size[1] * (scale * zoom)}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      >
        <Layer>
          <Image image={image} scaleX={scale * zoom} scaleY={scale * zoom} />
        </Layer>
        {mask && (
          <Layer>
            <Image image={mask} scaleX={scale * zoom} scaleY={scale * zoom} opacity={maskOpacity} />
          </Layer>
        )}
        {contour && (
          <Layer>
            <Image image={contour} scaleX={scale * zoom} scaleY={scale * zoom} opacity={contourOpacity} />
          </Layer>
        )}
        <Layer>
          {pointsInfo.map((point, i) => (
            <Point
              key={point.id}
              rectProps={point}
              scale={scale * zoom}
              strokeWidth={strokeWidth}
              isSelected={mode === "Transform" && point.id === selectedId}
              onClick={() => {
                if (mode === "Transform") {
                  setSelectedId(point.id);
                  setLabel(point.label);
                } else if (mode === "Del") {
                  setPointsInfo(pointsInfo.filter((p) => p.id !== point.id));
                }
              }}
              onChange={(newAttrs: any) => {
                const points = pointsInfo.slice();
                points[i] = newAttrs;
                setPointsInfo(points);
              }}
            />
          ))}
        </Layer>
        {selectionBox && (
          <Layer>
            <Rect
              x={selectionBox.x}
              y={selectionBox.y}
              width={selectionBox.width}
              height={selectionBox.height}
              stroke="blue"
              strokeWidth={1}
              dash={[4, 4]}
              fill="rgba(0, 0, 255, 0.2)"
            />
          </Layer>
        )}
      </Stage>
    </div>
  );
};

export default PointCanvas;
