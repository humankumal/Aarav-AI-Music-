import type {
  ArtistId, CatalogType, CatalogPage, CoverRunResult,
  CoverGeneration, CoverStats, CoverDraft, UploadReceipt, PipelineJobSummary, SongDraft, ConfigStatus,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// Health
export const getHealth = () => api<{ status: string }>("/health");

// Config
export const getConfigStatus = () => api<ConfigStatus>("/config/status");

// Cover catalog
export const getCoverCatalog = (
  catalogType: CatalogType,
  params?: { artist_id?: string; page?: number; per_page?: number }
) => {
  const q = new URLSearchParams();
  if (params?.artist_id) q.set("artist_id", params.artist_id);
  if (params?.page) q.set("page", String(params.page));
  if (params?.per_page) q.set("per_page", String(params.per_page));
  return api<CatalogPage>(`/covers/catalog/${catalogType}?${q}`);
};

// Cover generation
export const runCover = (body: {
  artist_id: ArtistId;
  song_id: string;
  catalog_type: CatalogType;
  emotion_intensity?: number;
}) => api<CoverRunResult>("/covers/run", { method: "POST", body: JSON.stringify(body) });

export const getCoverStatus = (song_id: string, artist_id: ArtistId) =>
  api<CoverGeneration>(`/covers/${song_id}/status?artist_id=${artist_id}`);

export const getGeneratedCovers = (artist_id: ArtistId, catalog_type?: CatalogType) => {
  const q = new URLSearchParams();
  if (catalog_type) q.set("catalog_type", catalog_type);
  return api<CoverGeneration[]>(`/covers/${artist_id}/generated?${q}`);
};

export const getCoverStats = () => api<CoverStats>("/covers/stats");

export const getCoverDraft = (song_id: string, artist_id: ArtistId) =>
  api<CoverDraft>(`/covers/${song_id}/draft?artist_id=${artist_id}`);

// Approvals
export const approveJob = (job_id: string, notes?: string) =>
  api(`/approvals/${job_id}/approve${notes ? `?notes=${encodeURIComponent(notes)}` : ""}`, {
    method: "POST",
  });

export const rejectJob = (job_id: string, notes?: string) =>
  api(`/approvals/${job_id}/reject${notes ? `?notes=${encodeURIComponent(notes)}` : ""}`, {
    method: "POST",
  });

// Pipeline
export const runPipeline = (body: {
  artist_id: ArtistId;
  theme: string;
  emotion_intensity?: number;
}) => api("/pipeline/run", { method: "POST", body: JSON.stringify(body) });

export const resumePipeline = (job_id: string) =>
  api(`/pipeline/resume/${job_id}`, { method: "POST" });

// Pipeline
export const runOriginalSong = (body: {
  artist_id: ArtistId;
  theme: string;
  emotion_intensity?: number;
  language?: string;
}) => api("/pipeline/run", { method: "POST", body: JSON.stringify(body) });

export const listPipelineJobs = (artist_id?: ArtistId) => {
  const q = artist_id ? `?artist_id=${artist_id}` : "";
  return api<PipelineJobSummary[]>(`/pipeline/jobs${q}`);
};

// Songs
export const listSongs = (artist_id: ArtistId) =>
  api<SongDraft[]>(`/songs/${artist_id}`);

// Uploads
export const listUploads = (artist_id: ArtistId) =>
  api<UploadReceipt[]>(`/uploads/${artist_id}`);
