export type StatusCode =
  | "on_track"
  | "watch"
  | "needs_attention"
  | "urgent"
  | "opportunity";

export interface StatusMeta {
  label: string;
  /** Pale fill + text pair for the pill treatment (StatusBadge). */
  classes: string;
  /** Saturated background for the rail and dot of the mark treatment (StatusMark). */
  accent: string;
}

export const STATUS_CLASSES: Record<StatusCode, StatusMeta> = {
  on_track: { label: "On Track", classes: "bg-green-100 text-green-700", accent: "bg-green-500" },
  watch: { label: "Watch", classes: "bg-amber-100 text-amber-700", accent: "bg-amber-500" },
  needs_attention: {
    label: "Needs Attention",
    classes: "bg-orange-100 text-orange-700",
    accent: "bg-orange-500",
  },
  urgent: { label: "Urgent", classes: "bg-red-100 text-red-700", accent: "bg-red-500" },
  opportunity: {
    label: "Opportunity",
    classes: "bg-teal-100 text-teal-700",
    accent: "bg-teal-500",
  },
};

export type WorkflowStatus =
  | "pending"
  | "in_review"
  | "in_progress"
  | "completed"
  | "overdue"
  | "blocked"
  | "approved";

export const WORKFLOW_STATUS_MAP: Record<WorkflowStatus, StatusCode> = {
  pending: "watch",
  in_review: "watch",
  in_progress: "on_track",
  completed: "on_track",
  approved: "on_track",
  overdue: "urgent",
  blocked: "needs_attention",
};
