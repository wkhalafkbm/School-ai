"use client";

import { useState, useMemo } from "react";
import StatusBadge from "./StatusBadge";
import { WORKFLOW_STATUS_MAP, WorkflowStatus } from "@/lib/status";

export interface WorkflowItem {
  id: string;
  stage: string;
  trigger: string;
  owner_name: string;
  owner_role: string;
  status: WorkflowStatus;
  description: string;
  due_date: string | null;
}

interface Props {
  items: WorkflowItem[];
}

export default function WorkflowList({ items }: Props) {
  const [stageFilter, setStageFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<WorkflowStatus | "">("");

  const stages = useMemo(
    () => Array.from(new Set(items.map((i) => i.stage))).sort(),
    [items]
  );

  const statuses = useMemo(
    () => Array.from(new Set(items.map((i) => i.status))).sort(),
    [items]
  );

  const visible = items.filter(
    (i) =>
      (stageFilter === "" || i.stage === stageFilter) &&
      (statusFilter === "" || i.status === statusFilter)
  );

  return (
    <div className="space-y-4">
      <div className="flex gap-4">
        <label className="flex items-center gap-2 text-sm">
          Filter by stage
          <select
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="">All stages</option>
            {stages.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm">
          Filter by status
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as WorkflowStatus | "")}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="">All statuses</option>
            {statuses.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs uppercase tracking-wide text-gray-500">
            <th className="pb-2 pr-4">Stage</th>
            <th className="pb-2 pr-4">Trigger</th>
            <th className="pb-2 pr-4">Owner</th>
            <th className="pb-2 pr-4">Role</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2">Due Date</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((item) => (
            <tr key={item.id} className="border-b last:border-0">
              <td className="py-2 pr-4 capitalize">{item.stage}</td>
              <td className="py-2 pr-4">{item.trigger}</td>
              <td className="py-2 pr-4">{item.owner_name}</td>
              <td className="py-2 pr-4">{item.owner_role}</td>
              <td className="py-2 pr-4">
                <StatusBadge code={WORKFLOW_STATUS_MAP[item.status]} />
              </td>
              <td className="py-2">{item.due_date ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
