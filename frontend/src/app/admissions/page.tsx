"use client";

import AdmissionsStageHeader, { AdmissionsStageSummary } from "@/components/AdmissionsStageHeader";
import ApplicantCard, { Applicant } from "@/components/ApplicantCard";
import PathwayRecommendation, { Recommendation } from "@/components/PathwayRecommendation";
import EvidencePanel, { Evidence } from "@/components/EvidencePanel";
import StreamedField from "@/components/StreamedField";
import { useStreamedProfile } from "@/lib/useStreamedProfile";
import AdmissionsActions from "./AdmissionsActions";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

interface AdmissionsProfile {
  stage_summary: AdmissionsStageSummary;
  applicant: Applicant;
  recommendation: Recommendation;
  evidence: Evidence;
}

export default function AdmissionsPage() {
  const { data, done } = useStreamedProfile<AdmissionsProfile>(
    `${API}/api/admissions/profile/stream`
  );

  if (!data) {
    return <main className="p-6 text-sm text-gray-500">Loading admissions profile…</main>;
  }

  const { stage_summary, applicant, recommendation, evidence } = data;

  return (
    <main className="space-y-6 p-6">
      <AdmissionsStageHeader summary={stage_summary} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ApplicantCard applicant={applicant} />
        <StreamedField resolved={done}>
          <PathwayRecommendation recommendation={recommendation} />
        </StreamedField>
      </div>

      <EvidencePanel evidence={evidence} />

      <div className="flex justify-end">
        <AdmissionsActions
          studentId={applicant.id}
          programName={applicant.program_name}
          recommendedAction={recommendation.action}
        />
      </div>
    </main>
  );
}
