/**
 * Minimal mock API server for Playwright E2E smoke tests.
 * Returns fixture-shaped responses for every page endpoint so Next.js
 * server components can render without a real backend or Docker Compose.
 */
import http from "node:http";

const ROUTES = {
  "/health": { status: "ok" },

  "/api/overview/metrics": {
    students_needing_attention: 3,
    at_risk_detected_early: 1,
    registration_issues_resolved: 0,
    graduation_delays_prevented: 1,
    faculty_overload_alerts: 1,
  },
  "/api/overview/journey-health": {
    onboarding: "watch",
    registration: "needs_attention",
    academic_progress: "urgent",
    graduation_planning: "urgent",
    career: "on_track",
  },
  "/api/overview/priority-queue": [
    {
      student_id: "stu-001",
      student_name: "Waleed Khalaf",
      stage: "admissions",
      status: "urgent",
      reason: "Pending sponsorship confirmation",
    },
  ],
  "/api/overview/chart-data": {
    enrollments_by_semester: [{ semester: "2024-Fall", count: 42 }],
    gpa_distribution: [
      { bucket: "<2.0", count: 2 },
      { bucket: "2.0-2.5", count: 5 },
      { bucket: "2.5-3.0", count: 10 },
      { bucket: "3.0-3.5", count: 18 },
      { bucket: "3.5-4.0", count: 7 },
    ],
    intervention_outcomes: [{ outcome: "improved", count: 3 }],
    lms_risk_by_semester: [{ semester: "2024-Fall", high: 2, medium: 4, low: 8 }],
  },

  "/api/admissions/profile": {
    stage_summary: {
      health: "needs_attention",
      total_applicants: 1,
      pending_review: 1,
      conditional_admits: 0,
      confirmed_enrollments: 0,
    },
    applicant: {
      id: "stu-001",
      name: "Waleed Khalaf",
      program_name: "Computer Science",
      year_level: 1,
      gpa: 3.7,
      sponsor: "KFAS",
      nationality: "Kuwaiti",
    },
    recommendation: {
      action: "Approve conditional admission pending transcript verification",
      confidence: 0.87,
      rationale: "Strong academic profile with verified sponsorship.",
    },
    evidence: {
      gpa: 3.7,
      test_score: 1320,
      recommendation_count: 2,
      datasource: "SIS",
    },
  },

  "/api/enrollment/profile": {
    stage_summary: {
      health: "needs_attention",
      registration_complete: 0,
      registration_pending: 1,
      registration_blocked: 1,
    },
    student: {
      id: "stu-002",
      name: "Mariam Al-Kandari",
      program_name: "Information Systems",
      year_level: 2,
      gpa: 3.1,
      onboarding_tasks: [
        { task_name: "Submit ID copy", category: "documents", completed: true, due_date: null },
        { task_name: "Pay tuition", category: "finance", completed: false, due_date: "2024-09-01" },
      ],
    },
    registration_blockers: [
      {
        type: "financial_hold",
        description: "Unpaid tuition balance.",
        rules_engine_result: "fail",
      },
    ],
    suggested_schedule: {
      sections: [
        {
          course: "CS201",
          section: "sec-002",
          days: ["Mon", "Wed"],
          time: "11:00-12:15",
          room: "Room 204",
        },
      ],
      note: "Avoids conflicting timeslots with existing holds.",
    },
  },

  "/api/teaching-readiness/profile": {
    stage_summary: {
      health: "watch",
      cohort_size: 42,
      aggregate_readiness_score: 0.74,
    },
    featured_course: {
      code: "CS101",
      name: "Introduction to Computer Science",
      slo_trends: [
        {
          slo_code: "SLO-001",
          description: "Apply fundamental algorithms",
          semesters: [
            { semester: "2023-Fall", proficiency_rate: 0.75 },
            { semester: "2024-Spring", proficiency_rate: 0.71 },
            { semester: "2024-Fall", proficiency_rate: 0.73 },
          ],
        },
        {
          slo_code: "SLO-002",
          description: "Implement data structures",
          semesters: [
            { semester: "2023-Fall", proficiency_rate: 0.68 },
            { semester: "2024-Spring", proficiency_rate: 0.63 },
            { semester: "2024-Fall", proficiency_rate: 0.60 },
          ],
        },
      ],
    },
    assessment_failure_rates: [
      {
        slo_code: "SLO-002",
        description: "Implement data structures",
        failure_rate: 0.4,
        rules_engine_result: "fail",
      },
    ],
    faculty_workload: [
      {
        id: "fac-001",
        name: "Dr. Ahmed Al-Rashidi",
        department: "Computer Science",
        current_credits: 15,
        max_credits: 12,
        overloaded: true,
        status: "urgent",
      },
    ],
    workload_threshold_result: "fail",
  },

  "/api/academic-risk/profile": {
    stage_summary: {
      health: "urgent",
      watch_count: 2,
      needs_attention_count: 3,
      urgent_count: 1,
    },
    student: {
      id: "stu-003",
      name: "Fahad Al-Ajmi",
      program_name: "Computer Science",
      year_level: 2,
      gpa: 2.4,
      academic_failure_risk: "urgent",
      attrition_risk: "needs_attention",
    },
    cohort_slo_pattern: [
      {
        slo_code: "SLO-002",
        description: "Data structures proficiency",
        student_score: 0.45,
        proficient: false,
        peers_underperforming: 8,
        cohort_size: 20,
      },
    ],
    intervention_plan: {
      actions: [
        {
          type: "tutoring_referral",
          description: "Refer to academic support centre for data structures tutoring",
          priority: "high",
        },
        {
          type: "advisor_meeting",
          description: "Schedule weekly check-in with faculty advisor",
          priority: "medium",
        },
      ],
      confidence: "High",
      rationale: "Pattern consistent with students who responded to early tutoring intervention.",
    },
    sponsor_escalation: {
      id: "wfl-006",
      trigger: "LMS risk flag raised",
      owner_name: "Noura Al-Hamdan",
      owner_role: "faculty advisor",
      status: "pending",
      created_date: "2024-10-17",
    },
  },

  "/api/progression/profile": {
    stage_summary: {
      health: "urgent",
      on_track_count: 3,
      at_risk_count: 2,
    },
    student: {
      id: "stu-004",
      name: "Noor Al-Hamad",
      program_name: "Information Systems",
      year_level: 3,
      gpa: 2.9,
    },
    credit_map: {
      total: { earned: 78, required: 130 },
      core: { earned: 54, required: 72 },
      math: { earned: 9, required: 12 },
      capstone: { completed: false, required: true },
      internship: { hours_completed: 0, hours_required: 120 },
      substitutions: [],
    },
    bottleneck_course: {
      course_code: "CS301",
      course_name: "Data Structures & Algorithms",
      section_capacity: 30,
      section_enrolled: 29,
      fill_rate: 0.97,
      constraint_type: "capacity",
      constraint_note: "Only 1 seat remaining in the only available section.",
    },
    cohort_delay_forecast: {
      students_at_risk: 2,
      total_cohort: 5,
    },
    bottleneck_slo_signal: {
      slo_code: "SLO-002",
      description: "Data structures proficiency",
      proficiency_rate: 0.6,
      cohort_size: 20,
      target_rate: 0.7,
      below_target: true,
    },
    graduation_risk_summary: {
      actions: [
        {
          type: "credit_recovery",
          description: "Enrol in summer session to close 12-credit deficit",
          priority: "high",
        },
      ],
      confidence: "High",
      rationale: "12-credit deficit identified — summer session recommended.",
    },
    plan_update_item: {
      id: "wfl-004",
      trigger: "Credits deficit detected",
      owner_name: "Dr. Bader Al-Otaibi",
      owner_role: "department chair",
      status: "in_review",
      created_date: "2024-10-22",
    },
  },

  "/api/career-alumni/profile": {
    stage_summary: {
      health: "opportunity",
      placement_rate: 0.88,
      median_time_to_placement: 3.2,
      employed_count: 7,
      total_graduates: 8,
    },
    student: {
      id: "stu-005",
      name: "Omar Al-Mutairi",
      program_name: "Computer Science",
      year_level: 4,
      gpa: 3.5,
      target_role: "Software Engineer",
      target_industry: "FinTech",
    },
    skill_gaps: [
      {
        skill: "System Design",
        current_level: "beginner",
        required_level: "intermediate",
        gap: true,
      },
    ],
    recommendations: {
      electives: [
        {
          course_code: "CS410",
          course_name: "Cloud Computing & Distributed Systems",
          rationale: "Closes cloud gap for FinTech senior roles",
        },
      ],
      internships: [
        {
          company: "NBK Digital",
          industry: "FinTech",
          target_semester: "Spring 2025",
          rationale: "Hands-on FinTech experience before graduation",
        },
      ],
    },
    alumni_mentor_match: {
      id: "alm-001",
      name: "Yousef Al-Babtain",
      current_role: "Senior Engineer",
      current_company: "Zain Kuwait",
      industry: "Telecommunications",
      graduation_year: 2019,
      program_name: "Computer Science",
      match_basis: "Shared program and target industry",
    },
    outcomes_feedback_loop: {
      description: "Recommendations refined from 8 graduate outcomes.",
      data_points: 8,
      last_updated: "2024-11-01",
    },
    career_pathway_recommendation: {
      actions: [
        {
          type: "skill_gap_elective",
          description: "Enrol in CS410 Cloud Computing to close infrastructure gap",
          priority: "high",
        },
      ],
      confidence: 0.82,
      rationale: "Strong GPA and aligned target industry.",
    },
    career_advisor_item: {
      id: "wfl-009",
      trigger: "Career pathway finalised",
      owner_name: "Lina Al-Enezi",
      owner_role: "career advisor",
      status: "pending",
      created_date: "2024-11-01",
    },
  },

  "/api/workflows": [
    {
      id: "wfl-001",
      stage: "admissions",
      trigger: "Application submitted",
      owner_name: "Sara Al-Rashidi",
      owner_role: "admissions officer",
      status: "in_review",
      due_date: "2024-09-01",
      description: "Review admissions dossier",
    },
  ],
};

const server = http.createServer((req, res) => {
  const url = req.url.split("?")[0];
  const body = ROUTES[url];
  if (body !== undefined) {
    res.writeHead(200, {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    });
    res.end(JSON.stringify(body));
  } else {
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: `No mock for ${url}` }));
  }
});

const PORT = parseInt(process.env.MOCK_API_PORT ?? "8001", 10);
server.listen(PORT, () => {
  process.stdout.write(`mock-api listening on :${PORT}\n`);
});
