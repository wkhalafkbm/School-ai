import AdmissionsStageHeader, { AdmissionsStageSummary } from "@/components/AdmissionsStageHeader";
import ApplicantCard, { Applicant } from "@/components/ApplicantCard";
import PathwayRecommendation, { Recommendation } from "@/components/PathwayRecommendation";
import EvidencePanel, { Evidence } from "@/components/EvidencePanel";
import AdmissionsActions from "./AdmissionsActions";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface AdmissionsProfile {
  stage_summary: AdmissionsStageSummary;
  applicant: Applicant;
  recommendation: Recommendation;
  evidence: Evidence;
}

async function fetchProfile(): Promise<AdmissionsProfile> {
  const res = await fetch(`${API}/api/admissions/profile`, { cache: "no-store" });
  if (!res.ok) throw new Error(`/api/admissions/profile → ${res.status}`);
  return res.json();
}

export default async function AdmissionsPage() {
  const { stage_summary, applicant, recommendation, evidence } = await fetchProfile();

  return (
    <main className="space-y-6 p-6">
      <AdmissionsStageHeader summary={stage_summary} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ApplicantCard applicant={applicant} />
        <PathwayRecommendation recommendation={recommendation} />
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
