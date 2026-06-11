export type StatusCode =
  | "on_track"
  | "watch"
  | "needs_attention"
  | "urgent"
  | "opportunity";

export interface StatusMeta {
  label: string;
  classes: string;
}

export const STATUS_CLASSES: Record<StatusCode, StatusMeta> = {
  on_track: { label: "On Track", classes: "bg-green-100 text-green-700" },
  watch: { label: "Watch", classes: "bg-amber-100 text-amber-700" },
  needs_attention: { label: "Needs Attention", classes: "bg-orange-100 text-orange-700" },
  urgent: { label: "Urgent", classes: "bg-red-100 text-red-700" },
  opportunity: { label: "Opportunity", classes: "bg-teal-100 text-teal-700" },
};
