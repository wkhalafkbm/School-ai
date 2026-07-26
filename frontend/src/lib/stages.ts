/**
 * The journey stage vocabulary — the frontend half of backend/app/stages.py.
 *
 * One value per journey stage, named after the nav entry that owns it, so a
 * stage carried by a workflow item, a priority-queue row or a journey-health
 * key routes and labels the same way everywhere (issue #68).
 *
 * backend/tests/test_stage_vocabulary.py fails if this list and the Python one
 * ever disagree.
 */

export const STAGES = [
  "admissions",
  "enrollment",
  "teaching_readiness",
  "academic_risk",
  "progression",
  "career_alumni",
] as const;

export type Stage = (typeof STAGES)[number];

export const STAGE_LABELS: Record<Stage, string> = {
  admissions: "Admissions",
  enrollment: "Enrollment",
  teaching_readiness: "Teaching Readiness",
  academic_risk: "Academic Risk",
  progression: "Progression",
  career_alumni: "Career & Alumni",
};

export const STAGE_ROUTES: Record<Stage, string> = {
  admissions: "/admissions",
  enrollment: "/enrollment",
  teaching_readiness: "/teaching-readiness",
  academic_risk: "/academic-risk",
  progression: "/progression",
  career_alumni: "/career-alumni",
};

/**
 * The stages the Overview journey-health map reports on. Teaching readiness is
 * absent because its health is a property of a cohort, not of a student moving
 * through the journey.
 */
export const JOURNEY_HEALTH_STAGES = [
  "admissions",
  "enrollment",
  "academic_risk",
  "progression",
  "career_alumni",
] as const satisfies readonly Stage[];

export type JourneyHealthStage = (typeof JOURNEY_HEALTH_STAGES)[number];
