"use client";
import type { CoverStatus } from "@/lib/types";

interface Props {
  onStatusChange: (status: CoverStatus | "") => void;
  selectedStatus: CoverStatus | "";
}

const STATUSES: Array<{ value: CoverStatus | ""; label: string }> = [
  { value: "", label: "All" },
  { value: "not_started", label: "Not Started" },
  { value: "generating", label: "Generating" },
  { value: "awaiting_approval", label: "Pending" },
  { value: "published", label: "Published" },
  { value: "failed", label: "Failed" },
];

export function CatalogFilters({ onStatusChange, selectedStatus }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {STATUSES.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => onStatusChange(value)}
          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            selectedStatus === value
              ? "bg-white text-black"
              : "bg-white/10 text-gray-300 hover:bg-white/20"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
