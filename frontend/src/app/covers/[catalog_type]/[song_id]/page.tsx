"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { LyricsPreview } from "@/components/shared/LyricsPreview";
import { ApprovalPanel } from "@/components/shared/ApprovalPanel";
import { GenerateButton } from "@/components/shared/GenerateButton";
import { getCoverStatus, getCoverDraft } from "@/lib/api-client";
import type { ArtistId, CatalogType, CoverDraft, CoverStatus } from "@/lib/types";

interface Props {
  params: { catalog_type: string; song_id: string };
}

const ARTIST_IDS: ArtistId[] = ["aarav", "aarohi"];

export default function SongDetailPage({ params }: Props) {
  const catalogType = params.catalog_type as CatalogType;
  const songId = params.song_id;

  const { data: aaravStatus } = useQuery({
    queryKey: ["coverStatus", songId, "aarav"],
    queryFn: () => getCoverStatus(songId, "aarav"),
  });

  const { data: aarohiStatus } = useQuery({
    queryKey: ["coverStatus", songId, "aarohi"],
    queryFn: () => getCoverStatus(songId, "aarohi"),
  });

  const referenceSongTitle =
    aaravStatus?.reference_song_title ?? aarohiStatus?.reference_song_title ?? songId;
  const referenceArtistName =
    aaravStatus?.reference_artist_name ?? aarohiStatus?.reference_artist_name ?? "";

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <div className="mb-6">
        <Link href={`/covers/${catalogType}`} className="text-xs text-gray-500 hover:text-gray-300">
          ← {catalogType === "nepali" ? "Nepali" : "Global"} Catalog
        </Link>
        <h1 className="text-2xl font-bold text-white mt-2">{referenceSongTitle}</h1>
        {referenceArtistName && (
          <p className="text-sm text-gray-400 mt-1">{referenceArtistName}</p>
        )}
        <span className="mt-2 inline-block rounded bg-white/10 px-2 py-0.5 text-[10px] text-gray-300 uppercase">
          {catalogType}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {ARTIST_IDS.map((artistId) => {
          const statusData = artistId === "aarav" ? aaravStatus : aarohiStatus;
          const status = (statusData?.status ?? "not_started") as CoverStatus;
          return (
            <ArtistPanel
              key={artistId}
              artistId={artistId}
              songId={songId}
              catalogType={catalogType}
              status={status}
              jobId={statusData?.job_id}
              referenceSongTitle={referenceSongTitle}
            />
          );
        })}
      </div>
    </main>
  );
}

function ArtistPanel({
  artistId,
  songId,
  catalogType,
  status,
  jobId,
  referenceSongTitle,
}: {
  artistId: ArtistId;
  songId: string;
  catalogType: CatalogType;
  status: CoverStatus;
  jobId?: string;
  referenceSongTitle: string;
}) {
  const queryClient = useQueryClient();
  const isAarav = artistId === "aarav";
  const accentColor = isAarav ? "border-[#e94560]/30" : "border-[#8B6914]/30";
  const headerColor = isAarav ? "text-[#e94560]" : "text-[#8B6914]";

  const { data: draft } = useQuery({
    queryKey: ["coverDraft", songId, artistId],
    queryFn: () => getCoverDraft(songId, artistId),
    enabled: status !== "not_started" && !!jobId,
    retry: false,
  });

  const handleGenerated = () => {
    queryClient.invalidateQueries({ queryKey: ["coverStatus", songId, artistId] });
  };

  const handleDecision = () => {
    queryClient.invalidateQueries({ queryKey: ["coverStatus", songId, artistId] });
    queryClient.invalidateQueries({ queryKey: ["coverDraft", songId, artistId] });
  };

  return (
    <div className={`rounded-xl border ${accentColor} bg-white/5 p-5 space-y-4`}>
      <div className="flex items-center justify-between">
        <h2 className={`font-bold text-lg ${headerColor} capitalize`}>{artistId}</h2>
        <StatusBadge status={status} />
      </div>

      {status === "not_started" && (
        <div className="pt-2">
          <p className="text-sm text-gray-400 mb-3">Not yet generated for this artist.</p>
          <GenerateButton
            artistId={artistId}
            songId={songId}
            catalogType={catalogType}
            onSuccess={handleGenerated}
          />
        </div>
      )}

      {status === "generating" && (
        <div className="flex items-center gap-2 py-4">
          <div className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" />
          <p className="text-sm text-gray-400">Gemini is writing lyrics…</p>
        </div>
      )}

      {(status === "awaiting_approval" || status === "phase1_complete" as CoverStatus) && draft && (
        <DraftView draft={draft} artistId={artistId} jobId={jobId} onDecision={handleDecision} />
      )}

      {status === "published" && draft && (
        <div className="space-y-4">
          <p className="text-xs text-green-400 font-medium">Published ✓</p>
          <LyricsPreview lyricsText={draft.lyrics.lyrics_text} />
        </div>
      )}

      {status === "failed" && (
        <div className="pt-2">
          <p className="text-sm text-red-400 mb-3">Generation failed.</p>
          <GenerateButton
            artistId={artistId}
            songId={songId}
            catalogType={catalogType}
            onSuccess={handleGenerated}
          />
        </div>
      )}
    </div>
  );
}

function DraftView({
  draft,
  artistId,
  jobId,
  onDecision,
}: {
  draft: CoverDraft;
  artistId: ArtistId;
  jobId?: string;
  onDecision: () => void;
}) {
  const { lyrics, metadata } = draft;

  return (
    <div className="space-y-5">
      {/* Song title + hook */}
      <div>
        <p className="text-base font-semibold text-white">{draft.song_title}</p>
        {lyrics.hook_line && (
          <p className="text-sm text-gray-400 italic mt-1">"{lyrics.hook_line}"</p>
        )}
      </div>

      {/* Mood tags */}
      {lyrics.mood_tags && lyrics.mood_tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {lyrics.mood_tags.map((tag) => (
            <span key={tag} className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] text-gray-300">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Emotional anchors */}
      {lyrics.emotional_anchors && lyrics.emotional_anchors.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">
            Emotional Anchors
          </p>
          <div className="flex flex-wrap gap-1.5">
            {lyrics.emotional_anchors.map((anchor) => (
              <span key={anchor} className="rounded bg-purple-900/40 border border-purple-700/30 px-2 py-0.5 text-[10px] text-purple-300">
                {anchor}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Core human experience */}
      {lyrics.core_human_experience && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
            Core Experience
          </p>
          <p className="text-sm text-gray-300 italic">{lyrics.core_human_experience}</p>
        </div>
      )}

      {/* YouTube title */}
      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
          YouTube Title
        </p>
        <p className="text-xs text-gray-300 bg-white/5 rounded p-2 break-words">{metadata.title}</p>
        <p className="text-[10px] text-gray-600 mt-0.5">SEO score: {metadata.seo_score}/100</p>
      </div>

      {/* Lyrics */}
      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Lyrics</p>
        <div className="max-h-64 overflow-y-auto rounded bg-black/30 p-3">
          <LyricsPreview lyricsText={lyrics.lyrics_text} />
        </div>
      </div>

      {/* Originality badge */}
      {lyrics.lyrics_are_original && (
        <p className="text-[10px] text-green-600">✓ Lyrics verified original</p>
      )}

      {/* Approval panel */}
      {jobId && (
        <ApprovalPanel
          jobId={jobId}
          songTitle={draft.song_title}
          onDecision={onDecision}
        />
      )}
    </div>
  );
}
