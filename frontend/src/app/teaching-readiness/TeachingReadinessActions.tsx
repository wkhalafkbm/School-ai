"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function TeachingReadinessActions() {
  const [open, setOpen] = useState(false);

  async function handleConfirm() {
    await fetch(`${API}/api/workflows`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stage: "teaching_readiness",
        trigger: "Cohort brief prepared — department chair approval required",
        owner_name: "Department Chair",
        owner_role: "department_chair",
        status: "pending",
        description:
          "Review cohort readiness brief and approve workload rebalancing before term start",
        student_id: null,
      }),
    });
    setOpen(false);
  }

  return (
    <>
      <button
        data-testid="prepare-cohort-brief-btn"
        onClick={() => setOpen(true)}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
      >
        Prepare Cohort Brief
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        >
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold text-gray-900">
              Confirm Cohort Brief
            </h2>
            <p className="mb-6 text-sm text-gray-600">
              This will create a workflow item assigned to the Department Chair
              for approval before any workload rebalancing task is assigned to
              faculty.
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
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
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
