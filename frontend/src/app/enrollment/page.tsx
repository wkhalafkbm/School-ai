import StatusBadge from "@/components/StatusBadge";
import { StatusCode } from "@/lib/status";
import EnrollmentActions from "./EnrollmentActions";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface OnboardingTask {
  task_name: string;
  category: string;
  completed: boolean;
  due_date: string | null;
}

interface RegistrationBlocker {
  type: string;
  description: string;
  rules_engine_result: "pass" | "fail" | "exception";
}

interface ScheduleSection {
  course: string;
  section: string;
  days: string[];
  time: string;
  room?: string;
  note?: string;
}

interface SuggestedSchedule {
  sections: ScheduleSection[];
  note: string;
}

interface EnrollmentProfile {
  stage_summary: {
    health: StatusCode;
    registration_complete: number;
    registration_pending: number;
    registration_blocked: number;
  };
  student: {
    id: string;
    name: string;
    program_name: string;
    year_level: number;
    gpa: number;
    onboarding_tasks: OnboardingTask[];
  };
  registration_blockers: RegistrationBlocker[];
  suggested_schedule: SuggestedSchedule;
}

async function fetchProfile(): Promise<EnrollmentProfile> {
  const res = await fetch(`${API}/api/enrollment/profile`, { cache: "no-store" });
  if (!res.ok) throw new Error(`/api/enrollment/profile → ${res.status}`);
  return res.json();
}

const BLOCKER_LABELS: Record<string, string> = {
  financial_aid_hold: "Financial Aid Hold",
  prerequisite: "Prerequisite",
  credit_limit: "Credit Limit",
  conflict: "Schedule Conflict",
  admin_hold: "Admin Hold",
  missing_document: "Missing Document",
};

const RESULT_CLASSES: Record<string, string> = {
  pass: "bg-green-100 text-green-700",
  fail: "bg-red-100 text-red-700",
  exception: "bg-amber-100 text-amber-700",
};

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between py-1 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  );
}

export default async function EnrollmentPage() {
  const { stage_summary, student, registration_blockers, suggested_schedule } =
    await fetchProfile();

  return (
    <main className="space-y-6 p-6">
      {/* Stage header */}
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Enrollment</h1>
        <StatusBadge code={stage_summary.health} />
        <div className="ml-auto flex gap-6 text-sm text-gray-600">
          <span>
            Complete:{" "}
            <strong>{stage_summary.registration_complete}</strong>
          </span>
          <span>
            Pending:{" "}
            <strong>{stage_summary.registration_pending}</strong>
          </span>
          <span>
            Blocked:{" "}
            <strong>{stage_summary.registration_blocked}</strong>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Student card */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-base font-semibold text-gray-900">
            {student.name}
          </h2>
          <Row label="Program" value={student.program_name} />
          <Row label="Year Level" value={student.year_level} />
          <Row label="GPA" value={student.gpa.toFixed(2)} />
        </div>

        {/* Onboarding checklist */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-base font-semibold text-gray-900">
            Onboarding Tasks
          </h2>
          <ul className="space-y-1.5">
            {student.onboarding_tasks.map((task) => (
              <li
                key={task.task_name}
                className="flex items-center gap-2 text-sm"
              >
                <span
                  className={
                    task.completed ? "text-green-600" : "text-gray-400"
                  }
                >
                  {task.completed ? "✓" : "○"}
                </span>
                <span
                  className={
                    task.completed ? "text-gray-700" : "text-gray-500"
                  }
                >
                  {task.task_name}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Registration blockers */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 text-base font-semibold text-gray-900">
          Registration Blockers
        </h2>
        <ul className="divide-y divide-gray-100">
          {registration_blockers.map((blocker) => (
            <li
              key={blocker.type}
              className="flex items-start justify-between gap-4 py-3"
            >
              <div className="flex items-start gap-3">
                <span className="mt-0.5 inline-flex min-w-[140px] items-center rounded px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-700">
                  {BLOCKER_LABELS[blocker.type] ?? blocker.type}
                </span>
                <span className="text-sm text-gray-700">{blocker.description}</span>
              </div>
              <span
                className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
                  RESULT_CLASSES[blocker.rules_engine_result] ?? ""
                }`}
              >
                {blocker.rules_engine_result}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* Suggested schedule */}
      <div
        data-testid="suggested-schedule"
        className="rounded-lg border border-blue-100 bg-blue-50 p-5"
      >
        <h2 className="mb-3 text-base font-semibold text-gray-900">
          Suggested Valid Schedule
        </h2>
        <ul className="mb-3 space-y-1.5">
          {suggested_schedule.sections.map((s) => (
            <li key={s.section} className="flex items-center gap-3 text-sm">
              <span className="font-mono font-medium text-blue-800">
                {s.section}
              </span>
              <span className="text-gray-600">
                {s.days.join("/")} · {s.time}
                {s.room ? ` · ${s.room}` : ""}
              </span>
              {s.note && (
                <span className="text-xs text-amber-600">{s.note}</span>
              )}
            </li>
          ))}
        </ul>
        <p className="text-sm text-gray-600">{suggested_schedule.note}</p>
      </div>

      {/* Action */}
      <div className="flex justify-end">
        <EnrollmentActions studentId={student.id} />
      </div>
    </main>
  );
}
