"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ScheduledClass {
  course_code: string;
  course_name: string;
  section_code: string;
  days: string[];
  start_time: string;
  end_time: string;
  room: string;
  credits: number | null;
}

export interface PlanTerm {
  term: string;
  is_current: boolean;
  source: string;
  classes: ScheduledClass[];
}

export interface GraduationPlan {
  student_id: string;
  student_name: string;
  terms: PlanTerm[];
}

/**
 * The academic week this data uses runs Sunday through Thursday. `key` is the
 * abbreviation the section records store in `days`.
 */
const WEEK = [
  { key: "Sun", label: "Sunday" },
  { key: "Mon", label: "Monday" },
  { key: "Tue", label: "Tuesday" },
  { key: "Wed", label: "Wednesday" },
  { key: "Thu", label: "Thursday" },
];

/** The teaching day the vertical axis spans, and how tall an hour of it is. */
const DAY_START_HOUR = 8;
const DAY_END_HOUR = 17;
const PX_PER_HOUR = 56;
const PX_PER_MINUTE = PX_PER_HOUR / 60;
const GRID_HEIGHT = (DAY_END_HOUR - DAY_START_HOUR) * PX_PER_HOUR;

const HOURS = Array.from(
  { length: DAY_END_HOUR - DAY_START_HOUR + 1 },
  (_, i) => DAY_START_HOUR + i
);

/** "11:00" → minutes since the top of the grid. */
function minutesFromDayStart(time: string): number {
  const [hours, minutes] = time.split(":").map(Number);
  return (hours - DAY_START_HOUR) * 60 + minutes;
}

/**
 * Where a class sits and how tall it is. Both axes read off the same
 * pixels-per-minute scale, so a block's height is its duration and its offset
 * is its start time.
 */
function blockGeometry(cls: ScheduledClass) {
  const start = minutesFromDayStart(cls.start_time);
  const end = minutesFromDayStart(cls.end_time);
  return {
    top: `${start * PX_PER_MINUTE}px`,
    height: `${(end - start) * PX_PER_MINUTE}px`,
  };
}

function Panel({ children }: { children: React.ReactNode }) {
  return (
    <section
      data-testid="weekly-calendar"
      className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
    >
      {children}
    </section>
  );
}

/**
 * The featured student's current-term class schedule as a Sunday–Thursday week.
 *
 * It fetches its own plan rather than riding the profile stream, so a slow or
 * broken schedule endpoint costs this panel and nothing else on the page.
 */
export default function WeeklyCalendar() {
  const [plan, setPlan] = useState<GraduationPlan | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    fetch(`${API}/api/progression/graduation-plan`, { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error(`graduation-plan → ${res.status}`);
        return res.json();
      })
      .then((body: GraduationPlan) => {
        if (!cancelled) setPlan(body);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (failed) {
    return (
      <Panel>
        <p className="text-sm text-gray-500">
          Couldn&apos;t load the class schedule.
        </p>
      </Panel>
    );
  }

  if (!plan) {
    return (
      <Panel>
        <p className="text-sm text-gray-500">Loading class schedule…</p>
      </Panel>
    );
  }

  const currentTerm = plan.terms.find((term) => term.is_current);

  if (!currentTerm) {
    return (
      <Panel>
        <h2 className="mb-2 text-base font-semibold text-gray-900">
          Class Schedule
        </h2>
        <p className="text-sm text-gray-500">
          No classes scheduled for the current term.
        </p>
      </Panel>
    );
  }

  return (
    <Panel>
      <div className="mb-4 flex items-baseline gap-3">
        <h2 className="text-base font-semibold text-gray-900">Class Schedule</h2>
        <span className="text-xs text-gray-500">
          Current term — {currentTerm.term}
        </span>
      </div>
      <table
        aria-label="Weekly class schedule"
        className="w-full table-fixed border-collapse"
      >
        <thead>
          <tr>
            <th scope="col" className="w-16 text-left text-xs text-gray-500">
              Time
            </th>
            {WEEK.map((day) => (
              <th
                key={day.key}
                scope="col"
                className="text-left text-xs font-medium text-gray-600"
              >
                {day.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            {/* Time axis — one label per hour, on the grid's own scale. */}
            <td className="relative align-top" style={{ height: GRID_HEIGHT }}>
              {HOURS.map((hour, index) => (
                <span
                  key={hour}
                  // Every label but the first is centred on its hour line; the
                  // first would ride up into the header row, so it hangs below.
                  className={`absolute right-2 text-[11px] text-gray-400 ${
                    index === 0 ? "" : "-translate-y-1/2"
                  }`}
                  style={{ top: `${(hour - DAY_START_HOUR) * PX_PER_HOUR}px` }}
                >
                  {String(hour).padStart(2, "0")}:00
                </span>
              ))}
            </td>
            {WEEK.map((day) => (
              <td
                key={day.key}
                data-testid={`day-column-${day.key}`}
                className="relative border-l border-gray-100 align-top"
                style={{ height: GRID_HEIGHT }}
              >
                {HOURS.slice(1).map((hour) => (
                  <div
                    key={hour}
                    aria-hidden
                    className="absolute inset-x-0 border-t border-gray-100"
                    style={{ top: `${(hour - DAY_START_HOUR) * PX_PER_HOUR}px` }}
                  />
                ))}
                {currentTerm.classes
                  .filter((cls) => cls.days.includes(day.key))
                  .map((cls) => (
                    <div
                      key={cls.section_code}
                      data-testid={`class-block-${cls.course_code}`}
                      title={`${cls.course_code} ${cls.course_name} · ${cls.section_code}`}
                      className="absolute inset-x-1 overflow-hidden rounded border border-blue-200 bg-blue-50 px-1.5 py-1 leading-tight"
                      style={blockGeometry(cls)}
                    >
                      <p
                        data-testid="class-code"
                        className="text-xs font-semibold text-gray-900"
                      >
                        {cls.course_code}
                      </p>
                      <p className="text-[11px] text-gray-600">
                        {cls.start_time}–{cls.end_time}
                      </p>
                      <p className="text-[11px] text-gray-500">{cls.room}</p>
                    </div>
                  ))}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </Panel>
  );
}
