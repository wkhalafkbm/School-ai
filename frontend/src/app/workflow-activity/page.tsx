import WorkflowList, { WorkflowItem } from "@/components/WorkflowList";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchWorkflows(): Promise<WorkflowItem[]> {
  const res = await fetch(`${API}/api/workflows`, { cache: "no-store" });
  if (!res.ok) throw new Error(`/api/workflows → ${res.status}`);
  return res.json();
}

export default async function WorkflowActivityPage() {
  const items = await fetchWorkflows();

  return (
    <main className="space-y-6 p-6">
      <h1>Workflow Activity</h1>
      <WorkflowList items={items} />
    </main>
  );
}
