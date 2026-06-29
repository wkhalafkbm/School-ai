import StatusBadge from "@/components/StatusBadge";
import { StatusCode } from "@/lib/status";
import CareerAlumniActions from "./CareerAlumniActions";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SkillGap {
  skill: string;
  current_level: string;
  required_level: string;
  gap: boolean;
}

interface ElectiveRecommendation {
  course_code: string;
  course_name: string;
  rationale: string;
}

interface InternshipRecommendation {
  company: string;
  industry: string;
  target_semester: string;
  rationale: string;
}

interface AlumniMentorMatch {
  id: string;
  name: string;
  current_role: string;
  current_company: string;
  industry: string;
  graduation_year: number;
  program_name: string;
  match_basis: string;
}

interface OutcomesFeedbackLoop {
  description: string;
  data_points: number;
  last_updated: string;
}

interface PathwayAction {
  type: string;
  description: string;
  priority: string;
}

interface CareerPathwayRecommendation {
  actions: PathwayAction[];
  confidence: string;
  rationale: string;
}

interface CareerAdvisorItem {
  id: string;
  trigger: string;
  owner_name: string;
  owner_role: string;
  status: string;
  created_date: string;
}

interface CareerAlumniProfile {
  stage_summary: {
    health: StatusCode;
    placement_rate: number;
    median_time_to_placement: number;
    employed_count: number;
    total_graduates: number;
  };
  student: {
    id: string;
    name: string;
    program_name: string;
    year_level: number;
    gpa: number;
    target_role: string;
    target_industry: string;
  };
  skill_gaps: SkillGap[];
  recommendations: {
    electives: ElectiveRecommendation[];
    internships: InternshipRecommendation[];
  };
  alumni_mentor_match: AlumniMentorMatch;
  outcomes_feedback_loop: OutcomesFeedbackLoop;
  career_pathway_recommendation: CareerPathwayRecommendation;
  career_advisor_item: CareerAdvisorItem | null;
}

async function fetchProfile(): Promise<CareerAlumniProfile> {
  const res = await fetch(`${API}/api/career-alumni/profile`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`/api/career-alumni/profile → ${res.status}`);
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

const LEVEL_CLASSES: Record<string, string> = {
  none: "bg-red-100 text-red-700",
  beginner: "bg-orange-100 text-orange-700",
  intermediate: "bg-amber-100 text-amber-700",
  advanced: "bg-green-100 text-green-700",
};

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between py-1 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  );
}

export default async function CareerAlumniPage() {
  const {
    stage_summary,
    student,
    skill_gaps,
    recommendations,
    alumni_mentor_match,
    outcomes_feedback_loop,
    career_pathway_recommendation,
    career_advisor_item,
  } = await fetchProfile();

  return (
    <main className="space-y-6 p-6">
      {/* Stage header */}
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Career &amp; Alumni</h1>
        <StatusBadge code={stage_summary.health} />
        <div className="ml-auto flex gap-6 text-sm text-gray-600">
          <span>
            Placement Rate:{" "}
            <strong>{Math.round(stage_summary.placement_rate * 100)}%</strong>
          </span>
          <span>
            Employed:{" "}
            <strong>
              {stage_summary.employed_count} of {stage_summary.total_graduates}
            </strong>
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
          <div>
            <Row label="Target Role" value={student.target_role} />
            <Row label="Target Industry" value={student.target_industry} />
          </div>
        </div>
      </div>

      {/* Skill gap analysis */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 text-base font-semibold text-gray-900">
          Skill Gap Analysis
        </h2>
        <p className="mb-3 text-xs text-gray-500">
          Skills assessed relative to {student.target_role} pathway requirements
        </p>
        <div className="space-y-3">
          {skill_gaps.map((sg) => (
            <div
              key={sg.skill}
              className="flex items-center justify-between gap-4 rounded-md border border-gray-100 px-3 py-2"
            >
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-800">{sg.skill}</p>
                <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                  <span>
                    Current:{" "}
                    <span
                      className={`inline-flex items-center rounded px-1.5 py-0.5 font-medium ${
                        LEVEL_CLASSES[sg.current_level] ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {sg.current_level}
                    </span>
                  </span>
                  <span>→</span>
                  <span>
                    Required:{" "}
                    <span className="inline-flex items-center rounded bg-blue-100 px-1.5 py-0.5 font-medium text-blue-700">
                      {sg.required_level}
                    </span>
                  </span>
                </div>
              </div>
              {sg.gap && (
                <span className="shrink-0 rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                  Gap
                </span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Elective recommendations */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 text-base font-semibold text-gray-900">
          Recommended Electives
        </h2>
        <div className="space-y-3">
          {recommendations.electives.map((elective) => (
            <div
              key={elective.course_code}
              className="rounded-md border border-gray-100 px-3 py-3"
            >
              <p className="text-sm font-medium text-gray-900">
                {elective.course_code} — {elective.course_name}
              </p>
              <p className="mt-1 text-xs text-gray-500">{elective.rationale}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Internship recommendations */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 text-base font-semibold text-gray-900">
          Recommended Internships
        </h2>
        <div className="space-y-3">
          {recommendations.internships.map((internship) => (
            <div
              key={internship.company}
              className="rounded-md border border-gray-100 px-3 py-3"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {internship.company}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-500">{internship.industry}</p>
                </div>
                <span className="shrink-0 text-xs text-gray-500">
                  {internship.target_semester}
                </span>
              </div>
              <p className="mt-2 text-xs text-gray-500">{internship.rationale}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Alumni mentor match */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-base font-semibold text-gray-900">
          Alumni Mentor Match
        </h2>
        <div className="space-y-1">
          <Row label="Mentor" value={alumni_mentor_match.name} />
          <Row label="Current Role" value={alumni_mentor_match.current_role} />
          <Row label="Company" value={alumni_mentor_match.current_company} />
          <Row label="Industry" value={alumni_mentor_match.industry} />
          <Row label="Program" value={alumni_mentor_match.program_name} />
          <Row label="Graduation Year" value={alumni_mentor_match.graduation_year} />
        </div>
        <div className="mt-3 rounded-md border border-blue-100 bg-blue-50 px-3 py-2">
          <p className="text-xs text-blue-700">
            <span className="font-medium">Match basis:</span>{" "}
            {alumni_mentor_match.match_basis}
          </p>
        </div>
      </section>

      {/* Outcomes feedback loop */}
      <section className="rounded-lg border border-green-200 bg-green-50 p-5">
        <h2 className="mb-2 text-base font-semibold text-gray-900">
          Outcomes Feedback Loop
        </h2>
        <p className="text-sm text-gray-700">
          {outcomes_feedback_loop.description}
        </p>
        <p className="mt-2 text-xs text-gray-500">
          Based on{" "}
          <strong>{outcomes_feedback_loop.data_points}</strong> graduate records
          · Last updated {outcomes_feedback_loop.last_updated}
        </p>
      </section>

      {/* Career pathway recommendation */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center gap-3">
          <h2 className="text-base font-semibold text-gray-900">
            Career Pathway Recommendation
          </h2>
          <span
            className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
              CONFIDENCE_CLASSES[career_pathway_recommendation.confidence] ?? ""
            }`}
          >
            {career_pathway_recommendation.confidence} Confidence
          </span>
        </div>
        <p className="mb-4 text-sm text-gray-600">
          {career_pathway_recommendation.rationale}
        </p>
        <ul className="space-y-2">
          {career_pathway_recommendation.actions.map((action) => (
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

      {/* Seeded career advisor workflow item */}
      {career_advisor_item && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-5">
          <h2 className="mb-2 text-base font-semibold text-gray-900">
            Career Advisor Review
          </h2>
          <p className="mb-3 text-xs text-amber-700">
            Auto-triggered on career pathway readiness signal
          </p>
          <div className="space-y-1 text-sm">
            <Row label="Trigger" value={career_advisor_item.trigger} />
            <Row
              label="Assigned To"
              value={`${career_advisor_item.owner_name} (${career_advisor_item.owner_role})`}
            />
            <Row label="Status" value={career_advisor_item.status} />
            <Row label="Created" value={career_advisor_item.created_date} />
          </div>
        </section>
      )}

      {/* Action */}
      <div className="flex justify-end">
        <CareerAlumniActions studentId={student.id} />
      </div>
    </main>
  );
}
