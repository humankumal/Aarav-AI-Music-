"use client";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { GenerateButton } from "@/components/shared/GenerateButton";
import type { CatalogSong, CoverStatus } from "@/lib/types";

interface Props {
  song: CatalogSong;
  aaravStatus?: CoverStatus;
  aarohi_status?: CoverStatus;
  onGenerated?: (jobId: string) => void;
}

export function CoverSongCard({ song, aaravStatus = "not_started", aarohi_status = "not_started", onGenerated }: Props) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3 hover:border-white/20 transition-colors">
      <div>
        <p className="font-semibold text-white truncate">{song.title}</p>
        <p className="text-xs text-gray-400 mt-0.5">{song.reference_artist_name}</p>
      </div>
      <span className="inline-block rounded bg-white/10 px-2 py-0.5 text-[10px] text-gray-300">
        {song.primary_language.toUpperCase()}
      </span>
      <div className="space-y-2 pt-1">
        <div className="flex items-center justify-between gap-2">
          <StatusBadge status={aaravStatus} />
          {aaravStatus === "not_started" && (
            <GenerateButton artistId="aarav" songId={song.song_id} catalogType={song.catalog_type} onSuccess={onGenerated} />
          )}
        </div>
        <div className="flex items-center justify-between gap-2">
          <StatusBadge status={aarohi_status} />
          {aarohi_status === "not_started" && (
            <GenerateButton artistId="aarohi" songId={song.song_id} catalogType={song.catalog_type} onSuccess={onGenerated} />
          )}
        </div>
      </div>
    </div>
  );
}
