"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { listUploads } from "@/lib/api-client";

export default function PublishingPage() {
  const { data: aaravUploads } = useQuery({
    queryKey: ["uploads", "aarav"],
    queryFn: () => listUploads("aarav"),
  });
  const { data: aarohiUploads } = useQuery({
    queryKey: ["uploads", "aarohi"],
    queryFn: () => listUploads("aarohi"),
  });

  const all = [...(aaravUploads ?? []), ...(aarohiUploads ?? [])].sort(
    (a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? "")
  );

  return (
    <main className="p-8 max-w-4xl mx-auto">
      <Link href="/" className="text-xs text-gray-500 hover:text-gray-300">← Dashboard</Link>
      <h1 className="text-2xl font-bold text-white mt-2">Publishing</h1>
      <p className="text-sm text-gray-400 mt-1 mb-6">Upload receipts and scheduled releases</p>
      {all.length === 0 ? (
        <p className="text-gray-500 text-sm">No uploads yet.</p>
      ) : (
        <div className="space-y-3">
          {all.map((receipt) => (
            <div key={receipt.job_id} className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-white">{receipt.song_title}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{receipt.artist_id} · {receipt.platform}</p>
                </div>
                <a
                  href={receipt.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-400 underline"
                >
                  View
                </a>
              </div>
              <p className="text-xs text-gray-500 mt-2">Job: {receipt.job_id?.slice(0, 8)}… · Status: {receipt.status}</p>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
