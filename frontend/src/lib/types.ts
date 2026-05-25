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

export interface SongDraft {
  job_id: string;
  artist_id: ArtistId;
  song_title: string;
  status: string;
  lyrics: {
    lyrics_text: string;
    hook_line: string;
    mood_tags: string[];
    suggested_titles: string[];
    language_detected?: string;
  };
  metadata: {
    title: string;
    seo_score: number;
    tags?: string[];
  };
  music_prompts?: {
    lyria_prompt: string;
  };
}

export interface PipelineJobSummary {
  job_id: string;
  artist_id: ArtistId;
  status: string;
  current_step: string;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  error_log?: Array<{ step: string; error: string }>;
}

export interface CoverDraft {
  job_id: string;
  artist_id: ArtistId;
  song_id: string;
  catalog_type: CatalogType;
  song_title: string;
  status: string;
  reference_song_title: string;
  reference_artist_name: string;
  lyrics: {
    lyrics_text: string;
    hook_line: string;
    suggested_titles: string[];
    mood_tags: string[];
    emotional_anchors?: string[];
    core_human_experience?: string;
    language_detected?: string;
    estimated_duration_seconds?: number;
    lyrics_are_original?: boolean;
  };
  metadata: {
    title: string;
    description: string;
    tags: string[];
    hashtags: string[];
    seo_score: number;
    cover_mode?: boolean;
    reference_song_title?: string;
  };
}

export interface ConfigStatus {
  credentials: Record<string, boolean>;
  mock_mode: boolean;
  environment: string;
  require_human_approval: boolean;
  all_required_set: boolean;
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
