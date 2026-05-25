"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { PipelineJobCard } from "@/components/shared/PipelineJobCard";
import { runOriginalSong, listPipelineJobs } from "@/lib/api-client";
import type { ArtistId } from "@/lib/types";

const THEMES = [
  { value: "heartbreak_rain", label: "Heartbreak Rain" },
  { value: "midnight_loneliness", label: "Midnight Loneliness" },
  { value: "spiritual_longing", label: "Spiritual Longing" },
  { value: "rainy_day", label: "Rainy Day" },
  { value: "nostalgia", label: "Nostalgia" },
  { value: "love_lost", label: "Love Lost" },
];

export default function PipelinePage() {
  const queryClient = useQueryClient();

  // Form state
  const [artistId, setArtistId] = useState<ArtistId>("aarav");
  const [theme, setTheme] = useState("heartbreak_rain");
  const [intensity, setIntensity] = useState(7);
  const [running, setRunning] = useState(false);
  const [lastResult, setLastResult] = useState<{ job_id: string; song_title: string } | null>(null);
  const [formError, setFormError] = useState("");

  // Jobs list — refetch every 5s to show live progress
  const { data: jobs } = useQuery({
    queryKey: ["pipelineJobs"],
    queryFn: () => listPipelineJobs(),
    refetchInterval: 5_000,
  });

  const activeJobs = (jobs ?? []).filter((j) =>
    j.status.includes("in_progress") || j.status === "awaiting_approval"
  );
  const recentJobs = (jobs ?? [])
    .filter((j) => !j.status.includes("in_progress") && j.status !== "awaiting_approval")
    .slice(0, 10);

  const handleGenerate = async () => {
    setRunning(true);
    setFormError("");
    setLastResult(null);
    try {
      const result = await runOriginalSong({ artist_id: artistId, theme, emotion_intensity: intensity });
      setLastResult({ job_id: result.job_id ?? "", song_title: result.song_title ?? "" });
      queryClient.invalidateQueries({ queryKey: ["pipelineJobs"] });
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <main className="p-8 max-w-5xl mx-auto space-y-10">
      <div>
        <Link href="/" className="text-xs text-gray-500 hover:text-gray-300">← Dashboard</Link>
        <h1 className="text-2xl font-bold text-white mt-2">Pipeline</h1>
        <p className="text-sm text-gray-400 mt-1">Trigger original song generation for Aarav or Aarohi</p>
      </div>

      {/* ── Trigger form ── */}
      <div className="rounded-2xl border border-white/10 bg-white/5 p-6 space-y-5">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Generate Original Song</h2>

        {/* Artist */}
        <div className="space-y-1.5">
          <label className="text-xs text-gray-500">Artist</label>
          <div className="flex gap-3">
            {(["aarav", "aarohi"] as ArtistId[]).map((id) => (
              <button
                key={id}
                onClick={() => setArtistId(id)}
                className={`flex-1 rounded-lg py-2.5 text-sm font-medium transition-colors ${
                  artistId === id
                    ? id === "aarav"
                      ? "bg-[#e94560] text-white"
                      : "bg-[#8B6914] text-white"
                    : "bg-white/10 text-gray-400 hover:bg-white/15"
                }`}
              >
                {id === "aarav" ? "Aarav" : "Aarohi"}
              </button>
            ))}
          </div>
        </div>

        {/* Theme */}
        <div className="space-y-1.5">
          <label className="text-xs text-gray-500">Theme</label>
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            className="w-full rounded-lg bg-white/10 px-3 py-2.5 text-sm text-gray-200 outline-none focus:ring-1 focus:ring-white/30"
          >
            {THEMES.map(({ value, label }) => (
              <option key={value} value={value} className="bg-gray-900">{label}</option>
            ))}
          </select>
        </div>

        {/* Intensity */}
        <div className="space-y-1.5">
          <label className="text-xs text-gray-500">
            Emotion Intensity — <span className="text-white font-medium">{intensity}/10</span>
          </label>
          <input
            type="range"
            min={1}
            max={10}
            value={intensity}
            onChange={(e) => setIntensity(Number(e.target.value))}
            className="w-full accent-[#e94560]"
          />
        </div>

        {formError && <p className="text-xs text-red-400">{formError}</p>}

        {lastResult && (
          <p className="text-xs text-green-400">
            ✓ Job started — <span className="font-mono">{lastResult.job_id.slice(0, 8)}…</span>
            {lastResult.song_title ? ` "${lastResult.song_title}"` : ""}
          </p>
        )}

        <button
          onClick={handleGenerate}
          disabled={running}
          className={`w-full rounded-lg py-3 text-sm font-semibold transition-colors ${
            artistId === "aarav"
              ? "bg-[#e94560] hover:bg-[#c73550]"
              : "bg-[#8B6914] hover:bg-[#7a5c11]"
          } text-white disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {running ? "Generating…" : `Generate ${artistId === "aarav" ? "Aarav" : "Aarohi"} — ${THEMES.find((t) => t.value === theme)?.label}`}
        </button>
      </div>

      {/* ── Active jobs ── */}
      {activeJobs.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
            Active Jobs ({activeJobs.length})
          </h2>
          {activeJobs.map((job) => (
            <PipelineJobCard key={job.job_id} job={job} />
          ))}
        </div>
      )}

      {/* ── Recent jobs ── */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
          Recent Jobs
        </h2>
        {recentJobs.length === 0 ? (
          <p className="text-sm text-gray-500">No completed jobs yet. Generate your first song above.</p>
        ) : (
          recentJobs.map((job) => (
            <PipelineJobCard key={job.job_id} job={job} />
          ))
        )}
      </div>
    </main>
  );
}
