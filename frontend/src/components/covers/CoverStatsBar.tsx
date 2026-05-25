import type { CoverStats } from "@/lib/types";

interface Props { stats: CoverStats }

export function CoverStatsBar({ stats }: Props) {
  const metrics = [
    { label: "Total Catalog", value: stats.catalog_total },
    { label: "Nepali Songs", value: stats.nepali_catalog },
    { label: "Global Songs", value: stats.global_catalog },
    { label: "Generated", value: stats.generated },
    { label: "Published", value: stats.status_breakdown?.published ?? 0 },
    { label: "Pending", value: (stats.status_breakdown?.generating ?? 0) + (stats.status_breakdown?.awaiting_approval ?? 0) },
  ];
  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
      {metrics.map(({ label, value }) => (
        <div key={label} className="rounded-lg bg-white/5 p-3 text-center">
          <p className="text-2xl font-bold text-white">{value}</p>
          <p className="mt-0.5 text-xs text-gray-400">{label}</p>
        </div>
      ))}
    </div>
  );
}
