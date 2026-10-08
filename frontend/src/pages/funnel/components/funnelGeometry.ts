/**
 * Builds the funnel SVG path - horizontal, flowing left to right.
 * Each stage is a vertical column; shape contracts as values decrease.
 */
export interface FunnelGeometry {
  svgWidth: number;
  svgHeight: number;
  stageWidth: number;
  pathD: string;
  gradientStops: { offset: string; color: string }[];
  stagePoints: { cx: number; topY: number; bottomY: number }[];
}

// Azuis da marca Vale Tec: do azul claro (topo do funil) ao azul-marinho (fundo)
const FUNNEL_COLORS = [
  "#8BBCE4",
  "#6AA9DE",
  "#4A97D6",
  "#3898E6",
  "#2A86D0",
  "#1977C4",
  "#1567AB",
  "#125891",
  "#0E4673",
  "#0B3456",
];

export const SVG_W = 900;
export const SVG_H = 260;
const CENTER_Y = SVG_H / 2;
const MAX_HALF_H = SVG_H / 2 - 10; // max half-height of the shape
const MIN_HALF_H = 4;               // min so the tip never collapses to zero

export function buildFunnelGeometry(
  values: number[],
  stageCount: number,
): FunnelGeometry {
  if (stageCount === 0) {
    return {
      svgWidth: SVG_W,
      svgHeight: SVG_H,
      stageWidth: 0,
      pathD: "",
      gradientStops: [],
      stagePoints: [],
    };
  }

  const stageWidth = SVG_W / stageCount;
  const maxValue = Math.max(...values, 1);

  // Compute the vertical half-height for each stage (centered)
  const stagePoints = values.map((v, i) => {
    const halfH = Math.max((v / maxValue) * MAX_HALF_H, MIN_HALF_H);
    const cx = stageWidth * i + stageWidth / 2;
    return { cx, topY: CENTER_Y - halfH, bottomY: CENTER_Y + halfH };
  });

  // Build top edge path (left → right)
  const topPts = stagePoints.map((p) => ({ x: p.cx, y: p.topY }));
  // Build bottom edge path (right → left, mirrored)
  const botPts = stagePoints.map((p) => ({ x: p.cx, y: p.bottomY })).reverse();

  const buildCurve = (
    pts: { x: number; y: number }[],
    startCmd: string,
  ): string => {
    let d = `${startCmd} ${pts[0].x} ${pts[0].y}`;
    for (let i = 1; i < pts.length; i++) {
      const prev = pts[i - 1];
      const curr = pts[i];
      const dx = (curr.x - prev.x) * 0.5;
      d += ` C ${prev.x + dx} ${prev.y}, ${curr.x - dx} ${curr.y}, ${curr.x} ${curr.y}`;
    }
    return d;
  };

  const pathD =
    buildCurve(topPts, "M") +
    ` L ${botPts[0].x} ${botPts[0].y}` +
    buildCurve(botPts, "").replace(/^[ML] \d+\.?\d* \d+\.?\d* ?/, "") +
    " Z";

  const gradientStops = Array.from({ length: stageCount }, (_, i) => ({
    offset: `${(i / Math.max(stageCount - 1, 1)) * 100}%`,
    color: FUNNEL_COLORS[i % FUNNEL_COLORS.length],
  }));

  return {
    svgWidth: SVG_W,
    svgHeight: SVG_H,
    stageWidth,
    pathD,
    gradientStops,
    stagePoints,
  };
}
