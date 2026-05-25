export type ArtistId = "aarav" | "aarohi";
export type CatalogType = "nepali" | "global";
export type CoverStatus = "not_started" | "generating" | "awaiting_approval" | "published" | "failed";
export type JobStatus = "in_progress" | "phase1_complete" | "awaiting_approval" | "phase2_complete" | "failed";

export interface CatalogSong {
  song_id: string;
  title: string;
  primary_language: string;
  reference_artist_id: string;
  reference_artist_name: string;
  catalog_type: CatalogType;
}

export interface CoverGeneration {
  song_id: string;
  artist_id: ArtistId;
  catalog_type: CatalogType;
  reference_artist_name: string;
  reference_song_title: string;
  status: CoverStatus;
  job_id?: string;
  youtube_url?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CoverStats {
  catalog_total: number;
  nepali_catalog: number;
  global_catalog: number;
  generated: number;
  status_breakdown: Record<string, number>;
}

export interface CatalogPage {
  catalog_type: CatalogType;
  total: number;
  page: number;
  per_page: number;
  songs: CatalogSong[];
}

export interface CoverRunResult {
  job_id: string;
  artist_id: ArtistId;
  song_id: string;
  catalog_type: CatalogType;
  song_title: string;
  status: string;
  reference_song_title: string;
  reference_artist_name: string;
  lyrics?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface PipelineJob {
  job_id: string;
  artist_id: ArtistId;
  status: JobStatus;
  current_step: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface UploadReceipt {
  job_id: string;
  artist_id: ArtistId;
  song_title: string;
  platform: string;
  video_id: string;
  url: string;
  status: string;
  created_at?: string;
}
