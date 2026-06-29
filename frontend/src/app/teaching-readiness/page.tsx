import StatusBadge from "@/components/StatusBadge";
import { StatusCode } from "@/lib/status";
import TeachingReadinessActions from "./TeachingReadinessActions";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SemesterRate {
  semester: string;
  proficiency_rate: number;
}

interface SloTrend {
  slo_code: string;
  description: string;
  semesters: SemesterRate[];
}

interface AssessmentFailureRate {
  slo_code: string;
  description: string;
  failure_rate: number;
  rules_engine_result: string;
}

interface FacultyWorkload {
  id: string;
  name: string;
  department: string;
  current_credits: number;
  max_credits: number;
  overloaded: boolean;
  status: StatusCode;
}

interface TeachingReadinessProfile {
  stage_summary: {
    health: StatusCode;
    cohort_size: number;
    aggregate_readiness_score: number;
  };
  featured_course: {
    code: string;
    name: string;
    slo_trends: SloTrend[];
  };
  assessment_failure_rates: AssessmentFailureRate[];
  faculty_workload: FacultyWorkload[];
  workload_threshold_result: string;
}

async function fetchProfile(): Promise<TeachingReadinessProfile> {
  const res = await fetch(`${API}/api/teaching-readiness/profile`, {
    cache: "no-store",
  });
  return res.json();
}

export default async function TeachingReadinessPage() {
  const data = await fetchProfile();
  const { stage_summary, featured_course, assessment_failure_rates, faculty_workload, workload_threshold_result } = data;
  const semesters = featured_course.slo_trends[0]?.semesters.map((s) => s.semester) ?? [];

  return (
    <main className="space-y-6 p-6">
      {/* Stage header */}
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Teaching Readiness</h1>
        <StatusBadge code={stage_summary.health} />
      </div>

      {/* Stage summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">Cohort Size</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{stage_summary.cohort_size}</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">Aggregate Readiness Score</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{stage_summary.aggregate_readiness_score}%</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">Workload Threshold</p>
          <p className="mt-1 font-semibold">
            <span
              className={
                workload_threshold_result === "fail"
                  ? "text-red-600 uppercase text-sm font-bold"
                  : "text-green-600 uppercase text-sm font-bold"
              }
            >
              {workload_threshold_result}
            </span>
          </p>
        </div>
      </div>

      {/* SLO Trend Table */}
      <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">
          SLO Achievement Trends — {featured_course.code}: {featured_course.name}
        </h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                <th className="py-2 pr-4 font-medium">SLO</th>
                {semesters.map((sem) => (
                  <th key={sem} className="py-2 pr-4 font-medium">{sem}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {featured_course.slo_trends.map((trend) => (
                <tr key={trend.slo_code} className="border-b border-gray-50">
                  <td className="py-2 pr-4 font-medium text-gray-900">{trend.slo_code}</td>
                  {trend.semesters.map((s) => (
                    <td key={s.semester} className="py-2 pr-4 text-gray-700">
                      {(s.proficiency_rate * 100).toFixed(1)}%
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Assessment Failure Rates */}
      <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">
          Assessment Failure Rate per SLO — Incoming Cohort
        </h2>
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
              <th className="py-2 pr-4 font-medium">SLO</th>
              <th className="py-2 pr-4 font-medium">Failure Rate</th>
              <th className="py-2 pr-4 font-medium">Rules Engine</th>
            </tr>
          </thead>
          <tbody>
            {assessment_failure_rates.map((r) => (
              <tr key={r.slo_code} className="border-b border-gray-50">
                <td className="py-2 pr-4 font-medium text-gray-900">{r.slo_code}</td>
                <td className="py-2 pr-4 text-gray-700">
                  {(r.failure_rate * 100).toFixed(1)}%
                </td>
                <td className="py-2 pr-4">
                  <span
                    className={
                      r.rules_engine_result === "fail"
                        ? "rounded bg-red-100 px-2 py-0.5 text-xs font-bold uppercase text-red-700"
                        : "rounded bg-green-100 px-2 py-0.5 text-xs font-bold uppercase text-green-700"
                    }
                  >
                    {r.rules_engine_result}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Faculty Workload */}
      <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Faculty Workload Distribution</h2>
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
              <th className="py-2 pr-4 font-medium">Faculty</th>
              <th className="py-2 pr-4 font-medium">Department</th>
              <th className="py-2 pr-4 font-medium">Credits</th>
              <th className="py-2 pr-4 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {faculty_workload.map((f) => (
              <tr key={f.id} className="border-b border-gray-50">
                <td className="py-2 pr-4 font-medium text-gray-900">{f.name}</td>
                <td className="py-2 pr-4 text-gray-600">{f.department}</td>
                <td className="py-2 pr-4 text-gray-700">
                  {f.current_credits} / {f.max_credits}
                </td>
                <td className="py-2 pr-4">
                  <StatusBadge code={f.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Action */}
      <div className="flex justify-end">
        <TeachingReadinessActions />
      </div>
    </main>
  );
}
