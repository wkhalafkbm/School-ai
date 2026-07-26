"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { StatusCode } from "@/lib/status";
import StatusMark from "./StatusMark";

export interface OverviewMetrics {
  students_needing_attention: number;
  at_risk_detected_early: number;
  registration_issues_resolved: number;
  graduation_delays_prevented: number;
  faculty_overload_alerts: number;
}

export interface MetricDetailRow {
  student_id: string;
  name: string;
  program_name: string;
  status: StatusCode;
  detail: string;
}

export interface MetricDetail {
  metric_key: string;
  definition: string;
  destination: { label: string; href: string };
  total: number;
  rows: MetricDetailRow[];
}

export type MetricKey = keyof OverviewMetrics;

const LABELS: Record<MetricKey, string> = {
  students_needing_attention: "Students Needing Attention",
  at_risk_detected_early: "At-Risk Detected Early",
  registration_issues_resolved: "Registration Issues Resolved",
  graduation_delays_prevented: "Graduation Delays Prevented",
  faculty_overload_alerts: "Faculty Overload Alerts",
};

export default function KpiCards({
  metrics,
  details = {},
}: {
  metrics: OverviewMetrics;
  details?: Partial<Record<MetricKey, MetricDetail>>;
}) {
  const keys = Object.keys(LABELS) as MetricKey[];
  const [openKey, setOpenKey] = useState<MetricKey | null>(null);
  const openDetail = openKey ? details[openKey] : undefined;

  useEffect(() => {
    if (!openKey) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpenKey(null);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [openKey]);

  return (
    <div>
      <div className="grid grid-cols-5 gap-4">
        {keys.map((key) => {
          const face = (
            <>
              <p className="text-sm text-gray-500">{LABELS[key]}</p>
              <p data-testid={`kpi-${key}`} className="mt-1 text-3xl font-bold text-gray-900">
                {metrics[key]}
              </p>
            </>
          );
          const shell = "rounded-lg border bg-white p-4 shadow-sm";

          if (!details[key]) {
            return (
              <div key={key} data-testid="kpi-card" className={shell}>
                {face}
              </div>
            );
          }

          return (
            <button
              key={key}
              type="button"
              data-testid="kpi-card"
              aria-expanded={openKey === key}
              onClick={() => setOpenKey((current) => (current === key ? null : key))}
              className={`${shell} text-left hover:bg-gray-50`}
            >
              {face}
            </button>
          );
        })}
      </div>

      {openDetail && (
        <div data-testid="kpi-drilldown" className="relative mt-3 rounded-lg border bg-white shadow-sm">
          {/* Caret sits over the centre of the card that opened the panel. */}
          <span
            data-testid="drilldown-caret"
            aria-hidden="true"
            style={{ left: `calc(${(keys.indexOf(openKey!) + 0.5) * (100 / keys.length)}% - 6px)` }}
            className="absolute -top-1.5 h-3 w-3 rotate-45 border-l border-t bg-white"
          />

          <div className="flex items-start justify-between gap-4 border-b px-4 py-2.5">
            <p data-testid="drilldown-definition" className="text-xs text-gray-500">
              {openDetail.definition}
            </p>
            <button
              type="button"
              onClick={() => setOpenKey(null)}
              aria-label="Close panel"
              className="shrink-0 text-sm text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          <ul className="divide-y">
            {openDetail.rows.map((row) => (
              <li
                key={row.student_id}
                data-testid="drilldown-row"
                className="flex items-center gap-4 px-4 py-2.5"
              >
                <StatusMark code={row.status} />
                <span className="w-48 shrink-0 text-sm font-medium text-gray-900">{row.name}</span>
                <span className="w-44 shrink-0 text-sm text-gray-600">{row.program_name}</span>
                <span className="flex-1 truncate text-sm text-gray-500">{row.detail}</span>
              </li>
            ))}
          </ul>

          <div
            data-testid="drilldown-footer"
            className="flex items-center justify-between border-t px-4 py-2.5 text-xs text-gray-500"
          >
            <span>
              Showing {openDetail.rows.length} of {openDetail.total}
            </span>
            <Link href={openDetail.destination.href} className="text-blue-600 hover:underline">
              View all in {openDetail.destination.label} →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
