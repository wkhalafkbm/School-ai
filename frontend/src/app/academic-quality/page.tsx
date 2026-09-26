"use client";

import { useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import MarkdownText from "@/components/MarkdownText";
import StreamedField from "@/components/StreamedField";
import { useStreamedProfile } from "@/lib/useStreamedProfile";
import { StatusCode } from "@/lib/status";
import WorkflowStrip, { WorkflowStep } from "./WorkflowStrip";
import AcademicQualityActions from "./AcademicQualityActions";
import AttainmentChain, { ProgramAttainment } from "./AttainmentChain";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface VarianceSection {
  section_id: string;
  section_code: string;
  instructor_id: string | null;
  instructor_name: string | null;
  proficiency_rate: number;
  assessed_students: number | null;
  proficient_count: number | null;
}

export interface RoutedItem {
  id: string;
  owner_name: string | null;
  owner_role: string | null;
  status: string;
  created_date: string;
}

/**
 * A marking inconsistency the engine flagged (#98): two sections of one course
 * whose proficiency on the same SLO in the same semester is `gap_points` apart.
 */
export interface ModerationVarianceFlag {
  course_id: string;
  course_code: string;
  course_name: string;
  slo_id: string;
  slo_code: string;
  slo_description: string;
  semester: string;
  sections: VarianceSection[];
  gap_points: number;
  threshold_points: number;
  trigger: string;
  moderation_owner_name: string;
  moderation_owner_role: string;
  routed_item: RoutedItem | null;
}

interface AcademicQualityProfile {
  stage_summary: {
    health: StatusCode;
    open_flag_count: number;
    routed_flag_count: number;
    plo_count: number;
    plos_below_target: number;
    attainment_target: number;
  };
  /** The SLO → CLO → PLO chain for the configured program (#97). */
  program_attainment: ProgramAttainment | null;
  moderation_variance_flags: ModerationVarianceFlag[];
  /**
   * Agent 10's narration (#99): why the flagged SLO matters for its PLO, what
   * the section gap suggests, and what to moderate first. Canned in the base
   * event; the agent's paragraph streams in as a field event.
   */
  diagnosis: string;
}

/** Where the quality workflow stands, read off the flags. */
function activeWorkflowStep(flags: ModerationVarianceFlag[], isRouted: (flag: ModerationVarianceFlag) => boolean): WorkflowStep {
  if (flags.length === 0) return "Diagnose";
  if (flags.some((flag) => !isRouted(flag))) return "Moderate";
  return "Validate";
}

function percent(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

function ModerationVarianceCard({
  flag,
  routed,
  onRouted,
}: {
  flag: ModerationVarianceFlag;
  routed: boolean;
  onRouted: (flag: ModerationVarianceFlag) => void;
}) {
  return (
    <section
      aria-label={`Moderation variance — ${flag.course_code} ${flag.slo_code}`}
      className="rounded-lg border border-red-200 bg-red-50 p-5"
    >
      <div className="mb-1 flex items-center gap-3">
        <h2 className="text-base font-semibold text-gray-900">Moderation variance</h2>
        <span className="inline-flex items-center rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
          {Math.round(flag.gap_points)} points apart
        </span>
      </div>
      <p className="mb-3 text-xs text-red-700">
        Two sections of one course differ on the same SLO by {flag.threshold_points}{" "}
        points or more — inconsistent marking needs human moderation.
      </p>

      <p className="font-medium text-gray-900">
        {flag.course_code} — {flag.course_name}
      </p>
      <p className="mt-1 text-sm text-gray-700">
        <span className="font-medium">{flag.slo_code}</span>: {flag.slo_description}
      </p>
      <p className="mt-1 text-xs text-gray-500">Assessed {flag.semester}</p>

      <table className="mt-3 w-full text-sm">
        <thead>
          <tr className="border-b border-red-200 text-left text-xs uppercase tracking-wide text-gray-500">
            <th className="pb-1 pr-4">Section</th>
            <th className="pb-1 pr-4">Instructor</th>
            <th className="pb-1 text-right">Proficient</th>
          </tr>
        </thead>
        <tbody>
          {flag.sections.map((section) => (
            <tr key={section.section_id}>
              <td className="py-1 pr-4 font-medium text-gray-900">{section.section_code}</td>
              <td className="py-1 pr-4 text-gray-700">
                {section.instructor_name ?? "Unassigned"}
              </td>
              <td className="py-1 text-right font-semibold text-gray-900">
                {percent(section.proficiency_rate)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-4 flex items-center justify-end gap-3">
        {routed ? (
          <p className="text-sm font-medium text-gray-700">
            Routed for moderation — {flag.moderation_owner_name}
            {flag.routed_item ? ` (${flag.routed_item.status})` : " (pending)"}
          </p>
        ) : (
          <AcademicQualityActions flag={flag} onRouted={onRouted} />
        )}
      </div>
    </section>
  );
}

export default function AcademicQualityPage() {
  const { data, done } = useStreamedProfile<AcademicQualityProfile>(
    `${API}/api/academic-quality/profile/stream`
  );
  // Flags routed in this session, so the strip and card move on without a
  // reload; a reload finds the same answer in the flag's routed_item.
  const [routedTriggers, setRoutedTriggers] = useState<Set<string>>(() => new Set());

  if (!data) {
    return (
      <main className="p-6 text-sm text-gray-500">Loading academic quality profile…</main>
    );
  }

  const { stage_summary, program_attainment, moderation_variance_flags, diagnosis } = data;
  const isRouted = (flag: ModerationVarianceFlag) =>
    flag.routed_item !== null || routedTriggers.has(flag.trigger);
  const markRouted = (flag: ModerationVarianceFlag) =>
    setRoutedTriggers((prev) => new Set(prev).add(flag.trigger));
  // Counted here rather than read off stage_summary so they move with the
  // card and the strip when a flag is routed in this session.
  const routedCount = moderation_variance_flags.filter(isRouted).length;
  const openCount = moderation_variance_flags.length - routedCount;

  return (
    <main className="space-y-6 p-6">
      <header className="space-y-2">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900">Moderation and Validation</h1>
          <StatusBadge code={stage_summary.health} />
          <div className="ml-auto flex gap-6 text-sm text-gray-600">
            <span>
              PLOs below target: <strong>{stage_summary.plos_below_target}</strong> of{" "}
              {stage_summary.plo_count}
            </span>
            <span>
              Open flags: <strong>{openCount}</strong>
            </span>
            <span>
              Routed: <strong>{routedCount}</strong>
            </span>
          </div>
        </div>
        <p className="text-sm text-gray-600">
          Program learning outcomes, assessment quality and accreditation readiness
          across programs. The engine flags anomalous marking and routes the evidence
          for human moderation.
        </p>
      </header>

      {program_attainment && <AttainmentChain program={program_attainment} />}

      {moderation_variance_flags.length === 0 ? (
        <p className="rounded-lg border border-gray-200 bg-white p-5 text-sm text-gray-600 shadow-sm">
          No marking variance detected between sections this semester.
        </p>
      ) : (
        moderation_variance_flags.map((flag) => (
          <ModerationVarianceCard
            key={flag.trigger}
            flag={flag}
            routed={isRouted(flag)}
            onRouted={markRouted}
          />
        ))
      )}

      <section
        aria-label="Diagnosis"
        className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
      >
        <h2 className="mb-2 text-base font-semibold text-gray-900">Diagnosis</h2>
        <div className="text-sm text-gray-700">
          <StreamedField resolved={done}>
            <MarkdownText text={diagnosis} />
          </StreamedField>
        </div>
      </section>

      <WorkflowStrip activeStep={activeWorkflowStep(moderation_variance_flags, isRouted)} />
    </main>
  );
}
