import { StatusChip, type Tone } from "@/components/ui/primitives";

function priorityTone(priority: string | null | undefined): Tone {
  const p = (priority ?? "").toLowerCase();
  if (p === "emergency" || p === "urgent") return "red";
  if (p === "high") return "amber";
  if (p === "low") return "gray";
  return "blue";
}

export function PriorityChip({ priority }: { priority: string | null | undefined }) {
  return <StatusChip tone={priorityTone(priority)}>{priority ? `${priority.charAt(0).toUpperCase()}${priority.slice(1)} priority` : "No priority"}</StatusChip>;
}
