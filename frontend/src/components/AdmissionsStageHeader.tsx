import StatusBadge from "./StatusBadge";
import { StatusCode } from "@/lib/status";

export interface AdmissionsStageSummary {
  health: StatusCode;
  applicant_count: number;
  pending_review_count: number;
}

export default function AdmissionsStageHeader({ summary }: { summary: AdmissionsStageSummary }) {
  return (
    <div className="flex items-center gap-4">
      <h1 className="text-2xl font-bold text-gray-900">Admissions</h1>
      <span data-testid="health-badge">
        <StatusBadge code={summary.health} />
      </span>
      <div className="ml-auto flex gap-6 text-sm text-gray-600">
        <span>
          Applicants:{" "}
          <strong data-testid="applicant-count">{summary.applicant_count}</strong>
        </span>
        <span>
          Pending Review:{" "}
          <strong data-testid="pending-review-count">{summary.pending_review_count}</strong>
        </span>
      </div>
    </div>
  );
}
