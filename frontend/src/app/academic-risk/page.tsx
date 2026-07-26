"use client";

import { useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import MarkdownText from "@/components/MarkdownText";
import StreamedField from "@/components/StreamedField";
import { useStreamedProfile } from "@/lib/useStreamedProfile";
import { StatusCode, WORKFLOW_STATUS_MAP, WorkflowStatus } from "@/lib/status";
import AcademicRiskActions from "./AcademicRiskActions";
import GpaBySemesterPanel, { type GpaTrend } from "./GpaBySemesterPanel";

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

/** An item this stage owns — including whatever the Approve button just wrote (#68). */
interface StageWorkflowItem {
  id: string;
  stage: string;
  trigger: string;
  owner_name: string | null;
  owner_role: string;
  status: WorkflowStatus;
  description: string | null;
  created_date: string | null;
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
  gpa_trend: GpaTrend;
  cohort_slo_pattern: SloPatternItem[];
  intervention_plan: InterventionPlan;
  sponsor_escalation: SponsorEscalation | null;
  workflow_items: StageWorkflowItem[];
  engagement_assessment: RationaleAssessment;
  support_assessment: RationaleAssessment;
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

/** Which risk lens the student card shows. The rest of the page is unaffected. */
type RiskLens = "snapshot" | "trend";

const LENSES: { value: RiskLens; label: string }[] = [
  { value: "snapshot", label: "Snapshot" },
  { value: "trend", label: "Trend" },
];

function LensToggle({
  lens,
  onChange,
}: {
  lens: RiskLens;
  onChange: (lens: RiskLens) => void;
}) {
  return (
    <div className="inline-flex rounded-md border border-gray-200 bg-gray-50 p-0.5">
      {LENSES.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={lens === option.value}
          onClick={() => onChange(option.value)}
          className={`rounded px-3 py-1 text-sm font-medium transition-colors ${
            lens === option.value
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between py-1 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  );
}

export default function AcademicRiskPage() {
  // Bumping the reload counter changes the stream URL, which is what the
  // profile hook re-subscribes on — how the page picks up an item the Approve
  // button just wrote (#68).
  const [reload, setReload] = useState(0);
  const { data, done } = useStreamedProfile<AcademicRiskProfile>(
    `${API}/api/academic-risk/profile/stream?reload=${reload}`
  );
  const [lens, setLens] = useState<RiskLens>("snapshot");

  if (!data) {
    return <main className="p-6 text-sm text-gray-500">Loading academic risk profile…</main>;
  }

  const {
    stage_summary,
    student,
    gpa_trend,
    cohort_slo_pattern,
    intervention_plan,
    sponsor_escalation,
    engagement_assessment,
    support_assessment,
    workflow_items,
  } = data;

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

      <LensToggle lens={lens} onChange={setLens} />

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
          {lens === "snapshot" ? (
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
          ) : (
            <div className="space-y-2 pt-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">GPA Trend</span>
                {gpa_trend.status ? (
                  <StatusBadge code={gpa_trend.status} />
                ) : (
                  <span className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                    No Trend Detected
                  </span>
                )}
              </div>
              <p className="text-xs leading-relaxed text-gray-500">
                {gpa_trend.reason}
              </p>
            </div>
          )}
        </div>
      </div>

      {lens === "trend" && <GpaBySemesterPanel trend={gpa_trend} />}

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
        <div className="text-sm text-gray-600">
          <StreamedField resolved={done}>
            <MarkdownText text={engagement_assessment.rationale} />
          </StreamedField>
        </div>
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
        <div className="mb-4 text-sm text-gray-600">
          <StreamedField resolved={done}>
            <MarkdownText text={intervention_plan.rationale} />
          </StreamedField>
        </div>
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

      {/* Everything open on this student at this stage, including what this
          page's own Approve button just created (#68). */}
      {workflow_items?.length > 0 && (
        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-base font-semibold text-gray-900">
            Open Workflow Items
          </h2>
          <ul className="divide-y">
            {workflow_items.map((item) => (
              <li key={item.id} className="flex items-center gap-4 py-2 text-sm">
                <span className="flex-1 text-gray-900">{item.trigger}</span>
                <span className="text-xs text-gray-500">
                  {item.owner_name ?? "Unassigned"} ({item.owner_role})
                </span>
                <StatusBadge code={WORKFLOW_STATUS_MAP[item.status]} />
                <span className="w-24 text-right text-xs text-gray-500">
                  {item.created_date ?? "—"}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

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
        <div className="text-sm text-gray-600">
          <StreamedField resolved={done}>
            <MarkdownText text={support_assessment.rationale} />
          </StreamedField>
        </div>
      </section>

      {/* Action */}
      <div className="flex justify-end">
        <AcademicRiskActions
          studentId={student.id}
          onCreated={() => setReload((n) => n + 1)}
        />
      </div>
    </main>
  );
}
