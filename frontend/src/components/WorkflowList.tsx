export interface WorkflowItem {
  id: string;
  stage: string;
  trigger: string;
  owner_name: string;
  owner_role: string;
  status: string;
  description: string;
  due_date: string | null;
}

interface Props {
  items: WorkflowItem[];
}

export default function WorkflowList({ items }: Props) {
  return (
    <ul>
      {items.map((item) => (
        <li key={item.id}>
          <span>{item.stage}</span>
          <span>{item.trigger}</span>
          <span>{item.owner_name}</span>
          <span>{item.status}</span>
        </li>
      ))}
    </ul>
  );
}
