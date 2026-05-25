"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { listSongs, listUploads, getCoverStats } from "@/lib/api-client";
import type { ArtistId, SongDraft, UploadReceipt } from "@/lib/types";

export default function AnalyticsPage() {
  const [artistId, setArtistId] = useState<ArtistId>("aarav");

  const { data: songs } = useQuery({
    queryKey: ["songs", artistId],
    queryFn: () => listSongs(artistId),
  });

  const { data: uploads } = useQuery({
    queryKey: ["uploads", artistId],
    queryFn: () => listUploads(artistId),
  });

  const { data: coverStats } = useQuery({
    queryKey: ["cover-stats"],
    queryFn: getCoverStats,
  });

  const kpis = computeKpis(songs ?? []);

  return (
    <main className="p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <Link href="/" className="text-xs text-gray-500 hover:text-gray-300">← Dashboard</Link>
        <h1 className="text-2xl font-bold text-white mt-2">Analytics</h1>
        <p className="text-sm text-gray-400 mt-1">Pipeline performance and publishing history</p>
      </div>

      {/* Artist tabs */}
      <div className="flex gap-3">
        {(["aarav", "aarohi"] as ArtistId[]).map((id) => (
          <button
            key={id}
            onClick={() => setArtistId(id)}
            className={`rounded-lg px-5 py-2 text-sm font-medium transition-colors ${
              artistId === id
                ? id === "aarav" ? "bg-[#e94560] text-white" : "bg-[#8B6914] text-white"
                : "bg-white/10 text-gray-400 hover:bg-white/15"
            }`}
          >
            {id === "aarav" ? "Aarav" : "Aarohi"}
          </button>
        ))}
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Songs Generated", value: kpis.total, color: "text-white" },
          { label: "Published", value: kpis.published, color: "text-green-400" },
          { label: "Pending Approval", value: kpis.pending, color: "text-yellow-400" },
          { label: "Failed", value: kpis.failed, color: "text-red-400" },
        ].map((tile) => (
          <div key={tile.label} className="rounded-xl border border-white/10 bg-white/5 p-4 text-center">
            <p className={`text-3xl font-bold ${tile.color}`}>{tile.value}</p>
            <p className="text-xs text-gray-500 mt-1">{tile.label}</p>
          </div>
        ))}
      </div>

      {/* Catalog coverage */}
      {coverStats && (
        <div className="rounded-xl border border-white/10 bg-white/5 p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-3">Catalog Coverage</p>
          <div className="flex items-center gap-4">
            <div className="flex-1 bg-white/10 rounded-full h-2.5 overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: `${Math.min(100, (coverStats.generated / coverStats.catalog_total) * 100)}%` }}
              />
            </div>
            <span className="text-sm text-gray-300 whitespace-nowrap">
              {coverStats.generated} / {coverStats.catalog_total} catalog songs covered
            </span>
          </div>
          <div className="flex gap-6 mt-3 text-xs text-gray-500">
            <span>Nepali: {coverStats.nepali_catalog}</span>
            <span>Global: {coverStats.global_catalog}</span>
            {Object.entries(coverStats.status_breakdown).map(([status, count]) => (
              <span key={status}>{status}: {count}</span>
            ))}
          </div>
        </div>
      )}

      {/* Publishing history */}
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-3">Publishing History</p>
        {!uploads || uploads.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-center">
            <p className="text-sm text-gray-400">No uploads yet.</p>
            <p className="text-xs text-gray-600 mt-1">
              Use{" "}
              <Link href="/pipeline" className="text-blue-400 underline">Pipeline</Link>
              {" "}or{" "}
              <Link href="/covers" className="text-blue-400 underline">Covers</Link>
              {" "}to generate and publish songs.
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-white/10 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left">
                  <th className="px-4 py-3 text-xs text-gray-500 font-medium">Song</th>
                  <th className="px-4 py-3 text-xs text-gray-500 font-medium">Platform</th>
                  <th className="px-4 py-3 text-xs text-gray-500 font-medium">Status</th>
                  <th className="px-4 py-3 text-xs text-gray-500 font-medium">Date</th>
                  <th className="px-4 py-3 text-xs text-gray-500 font-medium">Link</th>
                </tr>
              </thead>
              <tbody>
                {uploads.map((receipt, i) => (
                  <UploadRow key={receipt.job_id ?? i} receipt={receipt} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* YouTube Analytics placeholder */}
      <div className="rounded-xl border border-dashed border-white/20 bg-white/3 p-6">
        <p className="text-sm font-medium text-gray-300 mb-1">YouTube Analytics</p>
        <p className="text-xs text-gray-500 mb-3">
          Connect real YouTube credentials to see views, watch time, revenue, and audience data.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {["Views", "Watch Time", "Subscribers", "Revenue"].map((metric) => (
            <div key={metric} className="rounded-lg bg-white/5 p-3 text-center">
              <p className="text-lg font-semibold text-gray-600">—</p>
              <p className="text-[10px] text-gray-600 mt-0.5">{metric}</p>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-gray-600 mt-3">
          Requires <code className="bg-white/10 px-1 rounded">YOUTUBE_CREDENTIALS_PATH</code> +{" "}
          <code className="bg-white/10 px-1 rounded">GOOGLE_CLOUD_PROJECT</code> in your .env file.
        </p>
      </div>
    </main>
  );
}

function UploadRow({ receipt }: { receipt: UploadReceipt }) {
  const date = receipt.created_at
    ? new Date(receipt.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
    : "—";

  return (
    <tr className="border-b border-white/5 hover:bg-white/3 transition-colors">
      <td className="px-4 py-3 text-white">{receipt.song_title}</td>
      <td className="px-4 py-3 text-gray-400 capitalize">{receipt.platform}</td>
      <td className="px-4 py-3">
        <StatusBadge status={receipt.status as never} />
      </td>
      <td className="px-4 py-3 text-gray-500 text-xs">{date}</td>
      <td className="px-4 py-3">
        {receipt.url ? (
          <a
            href={receipt.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-400 hover:underline"
          >
            {receipt.url.includes("MOCK") ? "Mock URL" : "Watch"}
          </a>
        ) : (
          <span className="text-xs text-gray-600">—</span>
        )}
      </td>
    </tr>
  );
}

function computeKpis(songs: SongDraft[]) {
  const total = songs.length;
  const published = songs.filter((s) =>
    s.status === "phase2_complete" || s.status === "completed_phase2"
  ).length;
  const pending = songs.filter((s) =>
    s.status === "phase1_complete" || s.status === "completed_phase1" || s.status === "awaiting_approval"
  ).length;
  const failed = songs.filter((s) => s.status === "failed").length;
  return { total, published, pending, failed };
}
