import { clsx } from "clsx";
import type { CoverStatus } from "@/lib/types";

const STYLES: Record<CoverStatus, string> = {
  not_started: "bg-gray-700 text-gray-300",
  generating: "bg-blue-900 text-blue-300 animate-pulse",
  awaiting_approval: "bg-yellow-900 text-yellow-300",
  published: "bg-green-900 text-green-300",
  failed: "bg-red-900 text-red-400",
};
const LABELS: Record<CoverStatus, string> = {
  not_started: "Not Started",
  generating: "Generating…",
  awaiting_approval: "Awaiting Approval",
  published: "Published",
  failed: "Failed",
};

export function StatusBadge({ status }: { status: CoverStatus }) {
  return (
    <span className={clsx("inline-block rounded-full px-2 py-0.5 text-xs font-medium", STYLES[status])}>
      {LABELS[status]}
    </span>
  );
}
