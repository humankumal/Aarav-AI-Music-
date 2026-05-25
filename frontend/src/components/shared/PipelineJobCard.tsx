import { clsx } from "clsx";
import type { PipelineJobSummary } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  in_progress: "border-blue-500/40 bg-blue-950/20",
  in_progress_phase2: "border-blue-500/40 bg-blue-950/20",
  phase1_complete: "border-yellow-500/40 bg-yellow-950/20",
  completed_phase1: "border-yellow-500/40 bg-yellow-950/20",
  phase2_complete: "border-green-500/40 bg-green-950/20",
  completed_phase2: "border-green-500/40 bg-green-950/20",
  awaiting_approval: "border-orange-500/40 bg-orange-950/20",
  failed: "border-red-500/40 bg-red-950/20",
};

const STATUS_LABELS: Record<string, string> = {
  in_progress: "Running…",
  in_progress_phase2: "Phase 2 Running…",
  phase1_complete: "Phase 1 Done",
  completed_phase1: "Phase 1 Done",
  phase2_complete: "Complete ✓",
  completed_phase2: "Complete ✓",
  awaiting_approval: "Awaiting Approval",
  failed: "Failed",
};

const STEP_LABELS: Record<string, string> = {
  lyrics: "Writing lyrics",
  music_prompt: "Generating music prompt",
  metadata: "Building metadata",
  cover_lyrics: "Writing cover lyrics",
  music_generation: "Generating audio",
  audio_normalize: "Normalizing audio",
  lyric_video: "Building lyric video",
  thumbnail: "Rendering thumbnail",
  shorts: "Cutting Shorts",
  publishing: "Publishing to YouTube",
  done: "Done",
  awaiting_media_generation: "Waiting for media",
};

function elapsed(startedAt?: string): string {
  if (!startedAt) return "";
  const ms = Date.now() - new Date(startedAt).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

export function PipelineJobCard({ job }: { job: PipelineJobSummary }) {
  const borderStyle = STATUS_STYLES[job.status] ?? "border-white/10 bg-white/5";
  const statusLabel = STATUS_LABELS[job.status] ?? job.status;
  const stepLabel = STEP_LABELS[job.current_step] ?? job.current_step;
  const isRunning = job.status.includes("in_progress");
  const isFailed = job.status === "failed";
  const lastError = job.error_log?.[job.error_log.length - 1];

  return (
    <div className={clsx("rounded-xl border p-4 space-y-2", borderStyle)}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-gray-400">{job.job_id.slice(0, 8)}…</span>
          <span className={clsx(
            "inline-block rounded-full px-2 py-0.5 text-[10px] font-medium",
            job.artist_id === "aarav" ? "bg-[#e94560]/20 text-[#e94560]" : "bg-[#8B6914]/20 text-[#c9a96e]"
          )}>
            {job.artist_id}
          </span>
        </div>
        <span className="text-xs text-gray-300">{statusLabel}</span>
      </div>

      <div className="flex items-center gap-2">
        {isRunning && (
          <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse flex-shrink-0" />
        )}
        <span className="text-xs text-gray-400">{stepLabel}</span>
        {job.started_at && (
          <span className="ml-auto text-[10px] text-gray-600">{elapsed(job.started_at)}</span>
        )}
      </div>

      {isFailed && lastError && (
        <p className="text-[10px] text-red-400 bg-red-950/30 rounded p-2 break-words">
          {lastError.step}: {lastError.error}
        </p>
      )}
    </div>
  );
}
