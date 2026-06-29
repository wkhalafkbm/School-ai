"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function CareerAlumniActions({ studentId }: { studentId: string }) {
  const [open, setOpen] = useState(false);

  async function handleConfirm() {
    await fetch(`${API}/api/workflows`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stage: "career_alumni",
        trigger: "Career pathway recommendation approved — routing to career advisor",
        owner_name: "Career Advisor",
        owner_role: "career advisor",
        status: "pending",
        description:
          "Review and action Omar Al-Mutairi's career pathway recommendation, coordinate elective enrolment and internship outreach",
        student_id: studentId,
      }),
    });
    setOpen(false);
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
      >
        Recommend Career Path
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        >
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold text-gray-900">
              Confirm Career Path Recommendation
            </h2>
            <p className="mb-6 text-sm text-gray-600">
              This will route Omar Al-Mutairi&apos;s career pathway recommendation to a
              career advisor for review. The advisor will coordinate elective
              enrolment, internship outreach, and alumni mentor connection. No
              student outreach will occur without advisor approval.
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
