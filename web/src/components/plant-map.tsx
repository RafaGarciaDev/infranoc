"use client";

import { useRouter } from "next/navigation";
import type { NocPayload } from "@/lib/noc-ws";

type Area = NocPayload["plant"][number];

/**
 * Layout do mapa da planta (Fase 6).
 *
 * Grid 4 colunas x 3 linhas de retangulos. As posicoes sao fixas -
 * a ordem visual espelha o fluxo produtivo (recebimento -> pasteurizacao
 * -> linhas -> camaras -> expedicao) com utilidades/datacenter/lab de lado.
 */
const CELL_W = 170;
const CELL_H = 90;
const GAP = 12;

const LAYOUT: Record<string, { col: number; row: number }> = {
  recebimento:   { col: 0, row: 0 },
  pasteurizacao: { col: 1, row: 0 },
  laboratorio:   { col: 2, row: 0 },
  utilidades:    { col: 3, row: 0 },
  linha1:        { col: 0, row: 1 },
  linha2:        { col: 1, row: 1 },
  linha3:        { col: 2, row: 1 },
  linha4:        { col: 3, row: 1 },
  camaras:       { col: 0, row: 2 },
  expedicao:     { col: 1, row: 2 },
  datacenter:    { col: 2, row: 2 },
};

const SEVERITY_STYLE: Record<Area["severity"], { fill: string; stroke: string; pulse: boolean }> = {
  ok:       { fill: "#166534", stroke: "#22c55e", pulse: false },
  info:     { fill: "#1e40af", stroke: "#3b82f6", pulse: false },
  warning:  { fill: "#a16207", stroke: "#eab308", pulse: false },
  high:     { fill: "#9a3412", stroke: "#f97316", pulse: false },
  critical: { fill: "#991b1b", stroke: "#ef4444", pulse: true  },
};

type Props = { areas: Area[] };

export function PlantMap({ areas }: Props) {
  const router = useRouter();
  const cols = 4;
  const rows = 3;
  const width = cols * CELL_W + (cols + 1) * GAP;
  const height = rows * CELL_H + (rows + 1) * GAP;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-auto"
      role="img"
      aria-label="Mapa da planta Vale Verde"
    >
      <style>{`
        @keyframes noc-pulse {
          0%, 100% { opacity: 1; }
          50%      { opacity: 0.55; }
        }
        .noc-pulse { animation: noc-pulse 1.4s ease-in-out infinite; }
        .noc-tile  { cursor: pointer; transition: transform 120ms ease; }
        .noc-tile:hover { transform: translateY(-2px); }
      `}</style>

      {areas.map((area) => {
        const pos = LAYOUT[area.key];
        if (!pos) return null;
        const style = SEVERITY_STYLE[area.severity];
        const x = GAP + pos.col * (CELL_W + GAP);
        const y = GAP + pos.row * (CELL_H + GAP);
        return (
          <g
            key={area.key}
            className={`noc-tile ${style.pulse ? "noc-pulse" : ""}`}
            onClick={() => router.push(`/alertas?area=${encodeURIComponent(area.key)}`)}
          >
            <rect
              x={x} y={y} width={CELL_W} height={CELL_H} rx={10}
              fill={style.fill} stroke={style.stroke} strokeWidth={2}
            />
            <text
              x={x + CELL_W / 2} y={y + 32}
              textAnchor="middle" fill="#f8fafc"
              fontSize={15} fontWeight={600}
            >
              {area.label}
            </text>
            <text
              x={x + CELL_W / 2} y={y + 58}
              textAnchor="middle" fill="#e2e8f0"
              fontSize={13}
            >
              {area.count === 0 ? "sem alertas" : `${area.count} alerta${area.count > 1 ? "s" : ""}`}
            </text>
            <text
              x={x + CELL_W / 2} y={y + 78}
              textAnchor="middle" fill="#cbd5e1"
              fontSize={11} letterSpacing={0.6}
            >
              {area.severity.toUpperCase()}
            </text>
          </g>
        );
      })}
    </svg>
  );
}