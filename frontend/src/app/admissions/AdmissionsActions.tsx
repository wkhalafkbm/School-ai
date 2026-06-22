"use client";

import RecommendPathwayButton from "@/components/RecommendPathwayButton";

interface Props {
  studentId: string;
  programName: string;
  recommendedAction: string;
}

export default function AdmissionsActions({ studentId, programName, recommendedAction }: Props) {
  async function handleApprove() {
    await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/workflows`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stage: "admissions",
          trigger: "Pathway recommendation approved by admissions officer",
          owner_name: "Sara Al-Rashidi",
          owner_role: "admissions officer",
          status: "pending",
          description: `${recommendedAction} — ${programName}`,
          student_id: studentId,
        }),
      }
    );
  }

  return <RecommendPathwayButton onApprove={handleApprove} />;
}
