import StatusBadge from "@/components/StatusBadge";
import { StatusCode } from "@/lib/status";
import AcademicRiskActions from "./AcademicRiskActions";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SloPatternItem {
  slo_code: string;
  description: string;
  student_score: number;
  proficient: boolean;
  peers_underperforming: number;
  cohort_size: number;
}

interface InterventionAction {
  type: string;
  description: string;
  priority: string;
}

interface InterventionPlan {
  actions: InterventionAction[];
  confidence: string;
  rationale: string;
}

interface SponsorEscalation {
  id: string;
  trigger: string;
  owner_name: string;
  owner_role: string;
  status: string;
  created_date: string;
}

interface RationaleAssessment {
  rationale: string;
}

interface AcademicRiskProfile {
  stage_summary: {
    health: StatusCode;
    watch_count: number;
    needs_attention_count: number;
    urgent_count: number;
  };
  student: {
    id: string;
    name: string;
    program_name: string;
    year_level: number;
    gpa: number;
    academic_failure_risk: StatusCode;
    attrition_risk: StatusCode;
  };
  cohort_slo_pattern: SloPatternItem[];
  intervention_plan: InterventionPlan;
  sponsor_escalation: SponsorEscalation | null;
  engagement_assessment: RationaleAssessment;
  support_assessment: RationaleAssessment;
}

async function fetchProfile(): Promise<AcademicRiskProfile> {
  const res = await fetch(`${API}/api/academic-risk/profile`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`/api/academic-risk/profile → ${res.status}`);
  return res.json();
}

const CONFIDENCE_CLASSES: Record<string, string> = {
  High: "bg-green-100 text-green-700",
  Medium: "bg-amber-100 text-amber-700",
  Low: "bg-gray-100 text-gray-600",
};

const PRIORITY_CLASSES: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-blue-100 text-blue-700",
};

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between py-1 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  );
}

export default async function AcademicRiskPage() {
  const {
    stage_summary,
    student,
    cohort_slo_pattern,
    intervention_plan,
    sponsor_escalation,
    engagement_assessment,
    support_assessment,
  } = await fetchProfile();

  return (
    <main className="space-y-6 p-6">
      {/* Stage header */}
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Academic Risk</h1>
        <StatusBadge code={stage_summary.health} />
        <div className="ml-auto flex gap-6 text-sm text-gray-600">
          <span>
            Watch: <strong>{stage_summary.watch_count}</strong>
          </span>
          <span>
            Needs Attention: <strong>{stage_summary.needs_attention_count}</strong>
          </span>
          <span>
            Urgent: <strong>{stage_summary.urgent_count}</strong>
          </span>
        </div>
      </div>

      {/* Student card with dual risk indicators */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-base font-semibold text-gray-900">
          {student.name}
        </h2>
        <div className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
          <div>
            <Row label="Program" value={student.program_name} />
            <Row label="Year Level" value={student.year_level} />
            <Row label="GPA" value={student.gpa.toFixed(2)} />
          </div>
          <div className="space-y-2 pt-1">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Academic Failure Risk</span>
              <StatusBadge code={student.academic_failure_risk} />
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Attrition Risk</span>
              <StatusBadge code={student.attrition_risk} />
            </div>
          </div>
        </div>
      </div>

      {/* Cohort SLO pattern panel */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 text-base font-semibold text-gray-900">
          Cohort SLO Pattern
        </h2>
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
              <th className="py-2 pr-4 font-medium">SLO</th>
              <th className="py-2 pr-4 font-medium">Fahad's Score</th>
              <th className="py-2 pr-4 font-medium">Peers Also Underperforming</th>
            </tr>
          </thead>
          <tbody>
            {cohort_slo_pattern.map((item) => (
              <tr key={item.slo_code} className="border-b border-gray-50">
                <td className="py-2 pr-4">
                  <span className="font-medium text-gray-900">{item.slo_code}</span>
                  <p className="mt-0.5 text-xs text-gray-500">{item.description}</p>
                </td>
                <td className="py-2 pr-4 text-gray-700">
                  {item.student_score.toFixed(0)}
                </td>
                <td className="py-2 pr-4 text-gray-700">
                  {item.peers_underperforming} of {item.cohort_size}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Engagement & early risk detection assessment */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-base font-semibold text-gray-900">
          Engagement &amp; Early Risk Assessment
        </h2>
        <p className="text-sm text-gray-600">{engagement_assessment.rationale}</p>
      </section>

      {/* AI-generated intervention plan */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center gap-3">
          <h2 className="text-base font-semibold text-gray-900">
            Intervention Plan
          </h2>
          <span
            className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
              CONFIDENCE_CLASSES[intervention_plan.confidence] ?? ""
            }`}
          >
            {intervention_plan.confidence} Confidence
          </span>
        </div>
        <p className="mb-4 text-sm text-gray-600">{intervention_plan.rationale}</p>
        <ul className="space-y-2">
          {intervention_plan.actions.map((action) => (
            <li
              key={action.type}
              className="flex items-start justify-between gap-4 rounded-md border border-gray-100 px-3 py-2"
            >
              <span className="text-sm text-gray-700">{action.description}</span>
              <span
                className={`inline-flex shrink-0 items-center rounded px-2 py-0.5 text-xs font-medium ${
                  PRIORITY_CLASSES[action.priority] ?? ""
                }`}
              >
                {action.priority}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* Sponsor escalation (seeded, auto-triggered) */}
      {sponsor_escalation && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-5">
          <h2 className="mb-2 text-base font-semibold text-gray-900">
            Sponsor Escalation
          </h2>
          <p className="mb-3 text-xs text-amber-700">
            Auto-triggered at risk threshold
          </p>
          <div className="space-y-1 text-sm">
            <Row label="Trigger" value={sponsor_escalation.trigger} />
            <Row
              label="Assigned To"
              value={`${sponsor_escalation.owner_name} (${sponsor_escalation.owner_role})`}
            />
            <Row label="Status" value={sponsor_escalation.status} />
            <Row label="Created" value={sponsor_escalation.created_date} />
          </div>
        </section>
      )}

      {/* Student support & case management assessment */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-base font-semibold text-gray-900">
          Student Support &amp; Case Management
        </h2>
        <p className="text-sm text-gray-600">{support_assessment.rationale}</p>
      </section>

      {/* Action */}
      <div className="flex justify-end">
        <AcademicRiskActions studentId={student.id} />
      </div>
    </main>
  );
}
