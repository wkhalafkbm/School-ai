import StatusBadge from "@/components/StatusBadge";
import { StatusCode } from "@/lib/status";
import ProgressionActions from "./ProgressionActions";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface CreditEntry {
  earned: number;
  required: number;
}

interface Substitution {
  substituted_course: string;
  note: string;
}

interface CreditMap {
  total: CreditEntry;
  core: CreditEntry;
  math: CreditEntry;
  capstone: { completed: boolean; required: boolean };
  internship: { hours_completed: number; hours_required: number };
  substitutions: Substitution[];
}

interface BottleneckCourse {
  course_code: string;
  course_name: string;
  section_capacity: number;
  section_enrolled: number;
  fill_rate: number;
  constraint_type: string;
  constraint_note: string;
}

interface CohortDelayForecast {
  students_at_risk: number;
  total_cohort: number;
}

interface BottleneckSloSignal {
  slo_code: string;
  description: string;
  proficiency_rate: number;
  cohort_size: number;
  target_rate: number;
  below_target: boolean;
}

interface RiskAction {
  type: string;
  description: string;
  priority: string;
}

interface GraduationRiskSummary {
  actions: RiskAction[];
  confidence: string;
  rationale: string;
}

interface PlanUpdateItem {
  id: string;
  trigger: string;
  owner_name: string;
  owner_role: string;
  status: string;
  created_date: string;
}

interface ProgressionProfile {
  stage_summary: {
    health: StatusCode;
    on_track_count: number;
    at_risk_count: number;
  };
  student: {
    id: string;
    name: string;
    program_name: string;
    year_level: number;
    gpa: number;
  };
  credit_map: CreditMap;
  bottleneck_course: BottleneckCourse;
  cohort_delay_forecast: CohortDelayForecast;
  bottleneck_slo_signal: BottleneckSloSignal | null;
  graduation_risk_summary: GraduationRiskSummary;
  plan_update_item: PlanUpdateItem | null;
}

async function fetchProfile(): Promise<ProgressionProfile> {
  const res = await fetch(`${API}/api/progression/profile`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`/api/progression/profile → ${res.status}`);
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

function CreditBar({ earned, required }: { earned: number; required: number }) {
  const pct = Math.min(100, Math.round((earned / required) * 100));
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 rounded-full bg-gray-100">
        <div
          className="h-2 rounded-full bg-blue-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="shrink-0 text-xs text-gray-600">
        {earned} of {required}
      </span>
    </div>
  );
}

export default async function ProgressionPage() {
  const {
    stage_summary,
    student,
    credit_map,
    bottleneck_course,
    cohort_delay_forecast,
    bottleneck_slo_signal,
    graduation_risk_summary,
    plan_update_item,
  } = await fetchProfile();

  return (
    <main className="space-y-6 p-6">
      {/* Stage header */}
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Progression</h1>
        <StatusBadge code={stage_summary.health} />
        <div className="ml-auto flex gap-6 text-sm text-gray-600">
          <span>
            On-Track: <strong>{stage_summary.on_track_count}</strong>
          </span>
          <span>
            At-Risk: <strong>{stage_summary.at_risk_count}</strong>
          </span>
        </div>
      </div>

      {/* Student card */}
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
        </div>
      </div>

      {/* Credit map */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 text-base font-semibold text-gray-900">
          Credit Map &amp; Requirements
        </h2>
        <div className="space-y-3">
          <div>
            <div className="mb-1 flex justify-between text-xs text-gray-500">
              <span>Total Credits</span>
            </div>
            <CreditBar
              earned={credit_map.total.earned}
              required={credit_map.total.required}
            />
          </div>
          <div>
            <div className="mb-1 text-xs text-gray-500">Core Credits</div>
            <CreditBar
              earned={credit_map.core.earned}
              required={credit_map.core.required}
            />
          </div>
          <div>
            <div className="mb-1 text-xs text-gray-500">Math Credits</div>
            <CreditBar
              earned={credit_map.math.earned}
              required={credit_map.math.required}
            />
          </div>
          <div className="flex gap-6 pt-1 text-sm">
            <span className="text-gray-500">
              Capstone:{" "}
              <strong>
                {credit_map.capstone.completed ? "Complete" : "Incomplete"}
              </strong>
            </span>
            <span className="text-gray-500">
              Internship:{" "}
              <strong>
                {credit_map.internship.hours_completed} /{" "}
                {credit_map.internship.hours_required} hrs
              </strong>
            </span>
          </div>

          {credit_map.substitutions.length > 0 && (
            <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3">
              <p className="mb-1 text-xs font-medium text-amber-800">
                Substitutions
              </p>
              {credit_map.substitutions.map((sub, i) => (
                <div key={i} className="text-sm text-amber-700">
                  <strong>{sub.substituted_course}</strong> — {sub.note}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Bottleneck course — institutional constraint */}
      <section className="rounded-lg border border-orange-200 bg-orange-50 p-5">
        <h2 className="mb-1 text-base font-semibold text-gray-900">
          Bottleneck Course
        </h2>
        <p className="mb-3 text-xs text-orange-700">
          Institutional constraint — not a student planning failure
        </p>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-medium text-gray-900">
              {bottleneck_course.course_code} — {bottleneck_course.course_name}
            </p>
            <p className="mt-1 text-sm text-gray-600">
              {bottleneck_course.constraint_note}
            </p>
          </div>
          <div className="shrink-0 text-right text-sm">
            <p className="text-gray-500">Section capacity</p>
            <p className="font-semibold text-gray-900">
              {bottleneck_course.section_enrolled} of{" "}
              {bottleneck_course.section_capacity}
            </p>
          </div>
        </div>
      </section>

      {/* Cohort delay forecast */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-base font-semibold text-gray-900">
          Cohort Delay Forecast
        </h2>
        <p className="text-sm text-gray-600">
          <strong>{cohort_delay_forecast.students_at_risk}</strong> of{" "}
          <strong>{cohort_delay_forecast.total_cohort}</strong> students in this
          program face the same graduation delay risk.
        </p>
      </section>

      {/* Below-target SLO signal */}
      {bottleneck_slo_signal && (
        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-base font-semibold text-gray-900">
            Curriculum Signal — SLO Achievement
          </h2>
          <p className="mb-2 text-xs text-gray-500">
            Linked to bottleneck course: {bottleneck_course.course_code}
          </p>
          <div className="space-y-1">
            <Row label="SLO" value={bottleneck_slo_signal.slo_code} />
            <Row
              label="Description"
              value={bottleneck_slo_signal.description}
            />
            <Row
              label="Cohort Proficiency Rate"
              value={
                <span className="text-red-600">
                  {Math.round(bottleneck_slo_signal.proficiency_rate * 100)}%
                  {bottleneck_slo_signal.below_target && (
                    <span className="ml-1 text-xs font-normal text-red-500">
                      (below target {Math.round(bottleneck_slo_signal.target_rate * 100)}%)
                    </span>
                  )}
                </span>
              }
            />
          </div>
        </section>
      )}

      {/* AI graduation risk summary */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center gap-3">
          <h2 className="text-base font-semibold text-gray-900">
            Graduation Risk Summary
          </h2>
          <span
            className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
              CONFIDENCE_CLASSES[graduation_risk_summary.confidence] ?? ""
            }`}
          >
            {graduation_risk_summary.confidence} Confidence
          </span>
        </div>
        <p className="mb-4 text-sm text-gray-600">
          {graduation_risk_summary.rationale}
        </p>
        <ul className="space-y-2">
          {graduation_risk_summary.actions.map((action) => (
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

      {/* Seeded plan update workflow item */}
      {plan_update_item && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-5">
          <h2 className="mb-2 text-base font-semibold text-gray-900">
            Graduation Plan Update
          </h2>
          <p className="mb-3 text-xs text-amber-700">
            Auto-triggered on credit deficit detection
          </p>
          <div className="space-y-1 text-sm">
            <Row label="Trigger" value={plan_update_item.trigger} />
            <Row
              label="Assigned To"
              value={`${plan_update_item.owner_name} (${plan_update_item.owner_role})`}
            />
            <Row label="Status" value={plan_update_item.status} />
            <Row label="Created" value={plan_update_item.created_date} />
          </div>
        </section>
      )}

      {/* Action */}
      <div className="flex justify-end">
        <ProgressionActions studentId={student.id} />
      </div>
    </main>
  );
}
