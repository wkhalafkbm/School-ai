"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ProgressionActions({ studentId }: { studentId: string }) {
  const [open, setOpen] = useState(false);

  async function handleConfirm() {
    await fetch(`${API}/api/workflows`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stage: "progression",
        trigger: "Graduation plan update requested — routing to academic advisor",
        owner_name: "Academic Advisor",
        owner_role: "academic advisor",
        status: "pending",
        description:
          "Review and update Noor Al-Hamad's four-year graduation plan to address 12-credit deficit",
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
        Update Graduation Plan
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        >
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold text-gray-900">
              Confirm Graduation Plan Update
            </h2>
            <p className="mb-6 text-sm text-gray-600">
              This will route a plan update request to the academic advisor for
              review. The advisor will revise Noor Al-Hamad&apos;s four-year plan to
              address the 12-credit deficit.
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
