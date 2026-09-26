"use client";

import { useState } from "react";
import type { ModerationVarianceFlag } from "./page";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * "Route for moderation" (#98) — the human-in-the-loop step. Confirming files
 * a pending workflow item for the Programme Quality Lead under the
 * academic_quality stage, carrying the flag's own trigger so the profile can
 * report the flag as routed on the next load.
 */
export default function AcademicQualityActions({
  flag,
  onRouted,
}: {
  flag: ModerationVarianceFlag;
  onRouted: (flag: ModerationVarianceFlag) => void;
}) {
  const [open, setOpen] = useState(false);

  const [high, low] = flag.sections;
  const summary =
    `${high.section_code} ${Math.round(high.proficiency_rate * 100)}% vs ` +
    `${low.section_code} ${Math.round(low.proficiency_rate * 100)}%`;

  async function handleConfirm() {
    await fetch(`${API}/api/workflows`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stage: "academic_quality",
        trigger: flag.trigger,
        owner_name: flag.moderation_owner_name,
        owner_role: flag.moderation_owner_role,
        status: "pending",
        description:
          `Moderate ${flag.slo_code} marking for ${flag.course_code} (${flag.semester}): ` +
          `${summary}, ${Math.round(flag.gap_points)} points apart`,
        student_id: null,
      }),
    });
    setOpen(false);
    onRouted(flag);
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
      >
        Route for moderation
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        >
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold text-gray-900">
              Confirm Route for Moderation
            </h2>
            <p className="mb-6 text-sm text-gray-600">
              This will route the {flag.course_code} {flag.slo_code} marking evidence
              ({summary}) to the Programme Quality Lead for moderation. The item
              appears in Workflow Activity as pending.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setOpen(false)}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
