"use client";

import type { StatusCode } from "@/lib/status";

export interface GpaTermPoint {
  term: string;
  term_gpa: number | null;
  cumulative_gpa: number | null;
}

export interface TrendWorkflowItem {
  id: string;
  status: string;
  created_date: string;
}

export interface GpaTrend {
  series: GpaTermPoint[];
  /** null when no rule fired — there is no trend status to report. */
  status: StatusCode | null;
  reason: string;
  rules_fired: string[];
  workflow_item: TrendWorkflowItem | null;
}

/** GPA runs 0–4; fixing the axis keeps every student's chart comparable. */
const GPA_MAX = 4;
const CHART_WIDTH = 480;
const CHART_HEIGHT = 120;
const PADDING = 12;

const RULE_LABELS: Record<string, string> = {
  sharp_drop: "Sharp drop",
  sustained_decline: "Sustained decline",
};

function pointPosition(index: number, count: number, gpa: number) {
  const span = CHART_WIDTH - 2 * PADDING;
  // A single term has no span to distribute across — centre it.
  const x = count < 2 ? CHART_WIDTH / 2 : PADDING + (span * index) / (count - 1);
  const y =
    CHART_HEIGHT - PADDING - ((CHART_HEIGHT - 2 * PADDING) * gpa) / GPA_MAX;
  return { x, y };
}

function GpaLineChart({ series }: { series: GpaTrend["series"] }) {
  const plotted = series
    .map((point, index) => ({ point, index }))
    .filter(({ point }) => point.term_gpa !== null);

  const positions = plotted.map(({ point, index }) => ({
    term: point.term,
    gpa: point.term_gpa as number,
    ...pointPosition(index, series.length, point.term_gpa as number),
  }));

  return (
    <svg
      role="img"
      aria-label="Term GPA by semester"
      viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
      className="h-32 w-full"
    >
      <polyline
        fill="none"
        stroke="#2563eb"
        strokeWidth={2}
        points={positions.map((p) => `${p.x},${p.y}`).join(" ")}
      />
      {positions.map((p) => (
        <circle
          key={p.term}
          data-testid="gpa-chart-point"
          data-term={p.term}
          data-term-gpa={p.gpa}
          cx={p.x}
          cy={p.y}
          r={4}
          fill="#2563eb"
        />
      ))}
    </svg>
  );
}

export default function GpaBySemesterPanel({ trend }: { trend: GpaTrend }) {
  const { series, status, rules_fired, workflow_item } = trend;

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <h2 className="text-base font-semibold text-gray-900">GPA by Semester</h2>
        {status ? (
          rules_fired.map((rule) => (
            <span
              key={rule}
              data-testid="trend-rule"
              className="inline-flex items-center rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700"
            >
              {RULE_LABELS[rule] ?? rule}
            </span>
          ))
        ) : (
          <span className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
            No downward trend detected
          </span>
        )}
      </div>

      <GpaLineChart series={series} />

      <table aria-label="GPA by semester" className="mt-4 min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
            <th className="py-2 pr-4 font-medium">Term</th>
            <th className="py-2 pr-4 font-medium">Term GPA</th>
            <th className="py-2 pr-4 font-medium">Cumulative GPA</th>
          </tr>
        </thead>
        <tbody>
          {series.map((point) => (
            <tr key={point.term} className="border-b border-gray-50">
              <td className="py-2 pr-4 font-medium text-gray-900">{point.term}</td>
              <td className="py-2 pr-4 text-gray-700">
                {point.term_gpa === null ? "—" : point.term_gpa.toFixed(2)}
              </td>
              <td className="py-2 pr-4 text-gray-700">
                {point.cumulative_gpa === null
                  ? "—"
                  : point.cumulative_gpa.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* The intervention, reported alongside the trend — never in place of it.
          A completed item says someone acted, not that the GPA recovered. */}
      <div className="mt-4 border-t border-gray-100 pt-3 text-sm">
        <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500">
          Linked Workflow Item
        </h3>
        {workflow_item ? (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-gray-700">
            <span className="font-medium text-gray-900">{workflow_item.id}</span>
            <span>{workflow_item.status}</span>
            <span className="text-gray-500">
              opened {workflow_item.created_date}
            </span>
          </div>
        ) : (
          <p className="text-gray-500">No workflow item opened for this trend.</p>
        )}
      </div>
    </section>
  );
}
