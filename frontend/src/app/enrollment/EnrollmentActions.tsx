"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const WORKFLOW_ITEMS = [
  {
    owner_name: "Khalid Al-Fadli",
    owner_role: "registrar specialist",
    description: "Validate schedule and clear registration holds for Mariam Al-Kandari",
    trigger: "Schedule validated — registrar approval required",
  },
  {
    owner_name: "Finance Officer",
    owner_role: "financial aid officer",
    description: "Clear financial hold for Mariam Al-Kandari",
    trigger: "Schedule validated — financial aid clearance required",
  },
  {
    owner_name: "Document Verification Officer",
    owner_role: "student affairs officer",
    description: "Verify missing documents for Mariam Al-Kandari",
    trigger: "Schedule validated — document verification required",
  },
];

export default function EnrollmentActions({ studentId }: { studentId: string }) {
  const [open, setOpen] = useState(false);

  async function handleConfirm() {
    await Promise.all(
      WORKFLOW_ITEMS.map((item) =>
        fetch(`${API}/api/workflows`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            stage: "enrollment",
            trigger: item.trigger,
            owner_name: item.owner_name,
            owner_role: item.owner_role,
            status: "pending",
            description: item.description,
            student_id: studentId,
          }),
        })
      )
    );
    setOpen(false);
  }

  return (
    <>
      <button
        data-testid="validate-schedule-btn"
        onClick={() => setOpen(true)}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
      >
        Validate Schedule
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        >
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold text-gray-900">
              Confirm Schedule Validation
            </h2>
            <p className="mb-6 text-sm text-gray-600">
              This will create workflow items for the financial aid office, document
              verification, and the registrar simultaneously. Registration is not
              confirmed until all officers approve.
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
