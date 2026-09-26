"use client";

import { useState } from "react";

/**
 * The upward half of the deck's evidence chain (#97): Assessment → SLO → CLO →
 * PLO → program effectiveness. Each Program Learning Outcome is a bar against
 * the program's attainment target; a PLO expands to the courses feeding it
 * (the CLO level is each course's roll-up of the SLOs it contributes) and,
 * under each course, the SLOs with their rates and last assessed semester.
 */

export interface SloAttainment {
  slo_id: string;
  slo_code: string;
  description: string;
  proficiency_rate: number | null;
  on_target: boolean | null;
  last_assessed_semester: string | null;
  assessed_students: number | null;
  source: string | null;
  history: { semester: string; proficiency_rate: number }[];
}

export interface CourseAttainment {
  course_id: string;
  course_code: string;
  course_name: string;
  attainment: number | null;
  on_target: boolean | null;
  slos: SloAttainment[];
}

export interface PloAttainment {
  code: string;
  title: string;
  description: string;
  attainment: number | null;
  on_target: boolean | null;
  slo_count: number;
  assessed_slo_count: number;
  courses: CourseAttainment[];
}

export interface ProgramAttainment {
  program_id: string;
  program_name: string;
  attainment_target: number;
  latest_semester: string | null;
  plos_below_target: number;
  plos: PloAttainment[];
}

function percent(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

function rateClasses(onTarget: boolean | null): string {
  if (onTarget === null) return "text-gray-400";
  return onTarget ? "text-green-700" : "text-red-700";
}

function AttainmentBar({
  plo,
  target,
}: {
  plo: PloAttainment;
  target: number;
}) {
  const value = plo.attainment === null ? 0 : Math.round(plo.attainment * 100);
  const targetPercent = Math.round(target * 100);
  return (
    <div className="relative h-3 w-full rounded bg-gray-100">
      <div
        role="progressbar"
        aria-label={`${plo.code} attainment`}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        className={`h-3 rounded ${plo.on_target === false ? "bg-red-400" : "bg-green-500"}`}
        style={{ width: `${value}%` }}
      />
      <span
        aria-label={`${targetPercent}% target`}
        title={`${targetPercent}% target`}
        className="absolute -top-1 h-5 w-0.5 bg-gray-800"
        style={{ left: `${targetPercent}%` }}
      />
    </div>
  );
}

function SloRow({ slo }: { slo: SloAttainment }) {
  return (
    <li
      aria-label={slo.slo_code}
      className="flex flex-wrap items-baseline gap-x-3 gap-y-1 py-1.5 text-sm"
    >
      <span className="font-medium text-gray-900">{slo.slo_code}</span>
      <span className="flex-1 min-w-[12rem] text-gray-600">{slo.description}</span>
      {slo.proficiency_rate === null ? (
        <span className="text-xs italic text-gray-400">Not yet assessed</span>
      ) : (
        <>
          {slo.history.length > 1 && (
            <span
              className="text-xs text-gray-400"
              title={slo.history.map((h) => `${h.semester}: ${percent(h.proficiency_rate)}`).join(", ")}
            >
              {slo.history.map((h) => percent(h.proficiency_rate)).join(" → ")}
            </span>
          )}
          <span className={`font-semibold ${rateClasses(slo.on_target)}`}>
            {percent(slo.proficiency_rate)}
          </span>
          <span className="text-xs text-gray-500">Last assessed {slo.last_assessed_semester}</span>
        </>
      )}
    </li>
  );
}

function CourseGroup({ course }: { course: CourseAttainment }) {
  return (
    <div
      role="group"
      aria-label={`${course.course_code} — ${course.course_name}`}
      className="rounded-md border border-gray-200 bg-gray-50 px-4 py-3"
    >
      <div className="flex items-baseline justify-between gap-3">
        <p className="font-medium text-gray-900">
          {course.course_code} — {course.course_name}
        </p>
        {course.attainment === null ? (
          <span data-level="course" className="text-xs italic text-gray-400">
            Not yet assessed
          </span>
        ) : (
          <span data-level="course" className={`font-semibold ${rateClasses(course.on_target)}`}>
            {percent(course.attainment)}
          </span>
        )}
      </div>
      <ul className="mt-1 divide-y divide-gray-200">
        {course.slos.map((slo) => (
          <SloRow key={slo.slo_id} slo={slo} />
        ))}
      </ul>
    </div>
  );
}

function PloRow({
  plo,
  target,
  expanded,
  onToggle,
}: {
  plo: PloAttainment;
  target: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  const detailId = `plo-detail-${plo.code}`;
  return (
    <li>
      <div role="group" aria-label={`${plo.code} — ${plo.title}`} className="space-y-2">
        <div className="flex items-center gap-3">
          <button
            type="button"
            aria-expanded={expanded}
            aria-controls={detailId}
            onClick={onToggle}
            className="flex flex-1 items-center gap-2 text-left"
          >
            <span aria-hidden="true" className="text-gray-400">
              {expanded ? "▾" : "▸"}
            </span>
            <span className="font-semibold text-gray-900">{plo.code}</span>
            <span className="text-gray-700">{plo.title}</span>
          </button>
          <span className={`text-xs font-medium ${rateClasses(plo.on_target)}`}>
            {plo.on_target === null ? "Not yet assessed" : plo.on_target ? "On target" : "Below target"}
          </span>
          <span className={`w-12 text-right font-semibold ${rateClasses(plo.on_target)}`}>
            {plo.attainment === null ? "—" : percent(plo.attainment)}
          </span>
        </div>
        <AttainmentBar plo={plo} target={target} />
        <p className="text-xs text-gray-500">
          {plo.assessed_slo_count} of {plo.slo_count} SLOs assessed across {plo.courses.length}{" "}
          {plo.courses.length === 1 ? "course" : "courses"}
        </p>
        {expanded && (
          <div id={detailId} className="space-y-2 pt-1">
            <p className="text-xs text-gray-600">{plo.description}</p>
            {plo.courses.map((course) => (
              <CourseGroup key={course.course_id} course={course} />
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

export default function AttainmentChain({ program }: { program: ProgramAttainment }) {
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const toggle = (code: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });

  return (
    <section
      aria-label="Program learning outcomes"
      className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
    >
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-base font-semibold text-gray-900">Program learning outcomes</h2>
        <p className="text-xs text-gray-500">
          {program.program_name} · target {percent(program.attainment_target)}
          {program.latest_semester ? ` · latest assessment ${program.latest_semester}` : ""}
        </p>
      </div>
      <p className="mb-4 text-xs text-gray-600">
        Assessment → SLO → CLO → PLO → program effectiveness. Expand a PLO to see the
        courses feeding it and each course&apos;s SLOs.
      </p>
      <ul className="space-y-5">
        {program.plos.map((plo) => (
          <PloRow
            key={plo.code}
            plo={plo}
            target={program.attainment_target}
            expanded={expanded.has(plo.code)}
            onToggle={() => toggle(plo.code)}
          />
        ))}
      </ul>
    </section>
  );
}
