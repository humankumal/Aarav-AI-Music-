"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { CoverSongCard } from "@/components/covers/CoverSongCard";
import { CoverStatsBar } from "@/components/covers/CoverStatsBar";
import { CatalogFilters } from "@/components/covers/CatalogFilters";
import { getCoverCatalog, getCoverStats, getGeneratedCovers } from "@/lib/api-client";
import type { CatalogType, CoverStatus } from "@/lib/types";

interface Props {
  params: { catalog_type: string };
}

export default function CatalogPage({ params }: Props) {
  const catalogType = params.catalog_type as CatalogType;
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<CoverStatus | "">("");

  const { data: catalogData, isLoading: catalogLoading } = useQuery({
    queryKey: ["catalog", catalogType, page],
    queryFn: () => getCoverCatalog(catalogType, { page, per_page: 20 }),
  });

  const { data: stats } = useQuery({
    queryKey: ["coverStats"],
    queryFn: getCoverStats,
  });

  const { data: aaravCovers } = useQuery({
    queryKey: ["generatedCovers", "aarav", catalogType],
    queryFn: () => getGeneratedCovers("aarav", catalogType),
  });

  const { data: aarohiCovers } = useQuery({
    queryKey: ["generatedCovers", "aarohi", catalogType],
    queryFn: () => getGeneratedCovers("aarohi", catalogType),
  });

  const aaravStatusMap = Object.fromEntries(
    (aaravCovers ?? []).map((c) => [c.song_id, c.status])
  );
  const aarohiStatusMap = Object.fromEntries(
    (aarohiCovers ?? []).map((c) => [c.song_id, c.status])
  );

  const handleGenerated = () => {
    queryClient.invalidateQueries({ queryKey: ["generatedCovers"] });
    queryClient.invalidateQueries({ queryKey: ["coverStats"] });
  };

  const songs = catalogData?.songs ?? [];
  const filteredSongs = statusFilter
    ? songs.filter((s) => {
        const aaravS = aaravStatusMap[s.song_id] ?? "not_started";
        const aarohiS = aarohiStatusMap[s.song_id] ?? "not_started";
        return aaravS === statusFilter || aarohiS === statusFilter;
      })
    : songs;

  return (
    <main className="p-8 max-w-7xl mx-auto">
      <div className="mb-6">
        <Link href="/covers" className="text-xs text-gray-500 hover:text-gray-300">← Cover Songs</Link>
        <h1 className="text-2xl font-bold text-white mt-2 capitalize">{catalogType} Catalog</h1>
        {catalogData && (
          <p className="text-sm text-gray-400 mt-1">{catalogData.total} songs</p>
        )}
      </div>

      {stats && (
        <div className="mb-6">
          <CoverStatsBar stats={stats} />
        </div>
      )}

      <div className="mb-6">
        <CatalogFilters selectedStatus={statusFilter} onStatusChange={setStatusFilter} />
      </div>

      {catalogLoading ? (
        <div className="text-gray-400 text-sm">Loading catalog…</div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredSongs.map((song) => (
              <CoverSongCard
                key={song.song_id}
                song={song}
                aaravStatus={aaravStatusMap[song.song_id] as CoverStatus ?? "not_started"}
                aarohi_status={aarohiStatusMap[song.song_id] as CoverStatus ?? "not_started"}
                onGenerated={handleGenerated}
              />
            ))}
          </div>

          {catalogData && catalogData.total > 20 && (
            <div className="mt-8 flex items-center justify-center gap-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded px-4 py-2 text-sm bg-white/10 disabled:opacity-40 hover:bg-white/20"
              >
                Previous
              </button>
              <span className="text-sm text-gray-400">
                Page {page} of {Math.ceil(catalogData.total / 20)}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(catalogData.total / 20)}
                className="rounded px-4 py-2 text-sm bg-white/10 disabled:opacity-40 hover:bg-white/20"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </main>
  );
}
