"use client";

import { useState } from "react";

export interface GraduateOutcome {
  profile: string;
  outcome: string;
  cohort_size: number;
}

export interface Evidence {
  graduate_outcomes: GraduateOutcome[];
  signal_strength: "high" | "medium" | "low";
  data_completeness: "complete" | "partial" | "minimal";
}

export default function EvidencePanel({ evidence }: { evidence: Evidence }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-4 text-sm font-semibold text-gray-700 hover:bg-gray-50"
        aria-expanded={open}
      >
        <span>Evidence &amp; Supporting Data</span>
        <span className="text-gray-400">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="border-t border-gray-100 px-5 py-4 space-y-4">
          <div className="flex gap-6 text-sm">
            <span>
              Signal Strength:{" "}
              <strong data-testid="signal-strength">{evidence.signal_strength}</strong>
            </span>
            <span>
              Data Completeness:{" "}
              <strong data-testid="data-completeness">{evidence.data_completeness}</strong>
            </span>
          </div>

          <div data-testid="graduate-outcomes">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Graduate Outcomes — Similar Profiles
            </h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500">
                  <th className="pb-1 pr-4 font-medium">Profile</th>
                  <th className="pb-1 pr-4 font-medium">Outcome</th>
                  <th className="pb-1 font-medium">Cohort</th>
                </tr>
              </thead>
              <tbody>
                {evidence.graduate_outcomes.map((row, i) => (
                  <tr key={i} className="border-t border-gray-100">
                    <td className="py-1.5 pr-4 text-gray-700">{row.profile}</td>
                    <td className="py-1.5 pr-4 text-gray-700">{row.outcome}</td>
                    <td className="py-1.5 text-gray-700">{row.cohort_size}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
