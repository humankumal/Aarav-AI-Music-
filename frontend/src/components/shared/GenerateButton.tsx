"use client";
import { useState } from "react";
import { clsx } from "clsx";
import type { ArtistId, CatalogType } from "@/lib/types";
import { runCover } from "@/lib/api-client";

interface Props {
  artistId: ArtistId;
  songId: string;
  catalogType: CatalogType;
  onSuccess?: (jobId: string) => void;
}

export function GenerateButton({ artistId, songId, catalogType, onSuccess }: Props) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [jobId, setJobId] = useState<string | null>(null);

  const handleClick = async () => {
    setState("loading");
    try {
      const result = await runCover({ artist_id: artistId, song_id: songId, catalog_type: catalogType });
      setJobId(result.job_id);
      setState("done");
      onSuccess?.(result.job_id);
    } catch {
      setState("error");
    }
  };

  if (state === "done") return (
    <span className="text-xs text-green-400">Generated ✓ {jobId?.slice(0, 8)}</span>
  );
  if (state === "error") return (
    <button onClick={() => setState("idle")} className="text-xs text-red-400 underline">Failed — retry</button>
  );

  return (
    <button
      onClick={handleClick}
      disabled={state === "loading"}
      className={clsx(
        "rounded px-3 py-1.5 text-xs font-medium transition-colors",
        artistId === "aarav"
          ? "bg-[#e94560] hover:bg-[#c73550] text-white"
          : "bg-[#8B6914] hover:bg-[#7a5c11] text-white",
        state === "loading" && "opacity-50 cursor-not-allowed"
      )}
    >
      {state === "loading" ? "Generating…" : `Generate as ${artistId === "aarav" ? "Aarav" : "Aarohi"}`}
    </button>
  );
}
