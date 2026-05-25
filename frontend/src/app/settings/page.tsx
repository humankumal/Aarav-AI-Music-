"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getConfigStatus, getHealth } from "@/lib/api-client";
import type { ArtistId } from "@/lib/types";

const CREDENTIAL_LABELS: Record<string, { label: string; doc: string }> = {
  GEMINI_API_KEY:                 { label: "Gemini API Key",            doc: "Google AI Studio → API Keys" },
  FIREBASE_PROJECT_ID:            { label: "Firebase Project ID",        doc: "Firebase Console → Project Settings" },
  FIREBASE_STORAGE_BUCKET:        { label: "Firebase Storage Bucket",    doc: "Firebase Console → Storage" },
  YOUTUBE_CREDENTIALS_PATH:       { label: "YouTube OAuth Credentials",  doc: "Google Cloud Console → Credentials" },
  GOOGLE_CLOUD_PROJECT:           { label: "GCP Project ID",             doc: "Google Cloud Console → Dashboard" },
  GOOGLE_APPLICATION_CREDENTIALS: { label: "GCP Service Account Key",    doc: "Google Cloud Console → IAM → Service Accounts" },
};

const ARTIST_DEFAULTS = [
  { key: "emotion_intensity", label: "Default Emotion Intensity", aarav: "7 / 10", aarohi: "7 / 10" },
  { key: "shorts_count",      label: "Shorts per Release",        aarav: "2",      aarohi: "2" },
  { key: "publish_time",      label: "Preferred Publish Time",    aarav: "14:00 IST", aarohi: "14:00 IST" },
  { key: "language",          label: "Primary Language",          aarav: "Hindi",  aarohi: "Hindi" },
];

export default function SettingsPage() {
  const { data: configStatus, isLoading } = useQuery({
    queryKey: ["config-status"],
    queryFn: getConfigStatus,
  });

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
  });

  const allSet = configStatus?.all_required_set ?? false;
  const mockMode = configStatus?.mock_mode ?? true;

  return (
    <main className="p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <Link href="/" className="text-xs text-gray-500 hover:text-gray-300">← Dashboard</Link>
        <h1 className="text-2xl font-bold text-white mt-2">Settings</h1>
        <p className="text-sm text-gray-400 mt-1">API credentials and pipeline configuration</p>
      </div>

      {/* Pipeline mode banner */}
      <div className={`rounded-xl border p-4 flex items-center gap-3 ${
        mockMode
          ? "border-yellow-800/50 bg-yellow-900/20"
          : "border-green-800/50 bg-green-900/20"
      }`}>
        <span className={`text-xl ${mockMode ? "" : ""}`}>{mockMode ? "⚠" : "✓"}</span>
        <div>
          <p className={`text-sm font-medium ${mockMode ? "text-yellow-300" : "text-green-300"}`}>
            {mockMode ? "Mock Mode Active" : "Live Mode Active"}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            {mockMode
              ? "Pipeline runs without real AI calls. Set GEMINI_API_KEY to switch to live mode."
              : "All API credentials are configured. Pipeline will make real AI calls and upload to YouTube."}
          </p>
        </div>
        {health && (
          <span className="ml-auto text-[10px] text-gray-600 bg-white/10 rounded px-2 py-1">
            API {health.status}
          </span>
        )}
      </div>

      {/* API Credentials */}
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-3">API Credentials</p>
        <div className="rounded-xl border border-white/10 overflow-hidden">
          {isLoading ? (
            <p className="p-4 text-sm text-gray-500">Checking credentials…</p>
          ) : (
            Object.entries(CREDENTIAL_LABELS).map(([key, { label, doc }], i, arr) => {
              const isSet = configStatus?.credentials?.[key] ?? false;
              return (
                <div
                  key={key}
                  className={`flex items-center gap-4 px-4 py-3 ${
                    i < arr.length - 1 ? "border-b border-white/5" : ""
                  } hover:bg-white/3 transition-colors`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white">{label}</p>
                    <p className="text-[10px] text-gray-600 mt-0.5">{key}</p>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <span className={`text-[10px] text-gray-600`}>{doc}</span>
                    <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
                      isSet
                        ? "bg-green-900/50 text-green-300"
                        : "bg-red-900/30 text-red-400"
                    }`}>
                      {isSet ? "Set" : "Missing"}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
        <p className="text-[10px] text-gray-600 mt-2">
          Add missing keys to your <code className="bg-white/10 px-1 rounded">.env</code> file and restart the server.
          Values are never displayed here.
        </p>
      </div>

      {/* Pipeline defaults */}
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-3">Pipeline Defaults</p>
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <div className="grid grid-cols-3 border-b border-white/10 bg-white/3 px-4 py-2">
            <p className="text-[10px] text-gray-500">Setting</p>
            <p className="text-[10px] text-gray-500 text-center">Aarav</p>
            <p className="text-[10px] text-gray-500 text-center">Aarohi</p>
          </div>
          {ARTIST_DEFAULTS.map(({ key, label, aarav, aarohi }, i, arr) => (
            <div
              key={key}
              className={`grid grid-cols-3 px-4 py-3 ${
                i < arr.length - 1 ? "border-b border-white/5" : ""
              }`}
            >
              <p className="text-sm text-gray-300">{label}</p>
              <p className="text-sm text-center text-gray-400">{aarav}</p>
              <p className="text-sm text-center text-gray-400">{aarohi}</p>
            </div>
          ))}
          <div className="grid grid-cols-3 px-4 py-3 border-t border-white/5">
            <p className="text-sm text-gray-300">Require Human Approval</p>
            <p className="text-sm text-center col-span-2 text-gray-400">
              {configStatus?.require_human_approval ? "Yes" : "No"}
            </p>
          </div>
        </div>
        <p className="text-[10px] text-gray-600 mt-2">
          Edit <code className="bg-white/10 px-1 rounded">config/artists/aarav.json</code> and{" "}
          <code className="bg-white/10 px-1 rounded">config/artists/aarohi.json</code> to change defaults.
        </p>
      </div>

      {/* Quick links */}
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-3">Quick Links</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            { label: "Google AI Studio", sub: "Get Gemini API key", href: "https://aistudio.google.com/app/apikey" },
            { label: "Firebase Console", sub: "Firestore + Storage", href: "https://console.firebase.google.com" },
            { label: "GCP Console", sub: "Vertex AI + IAM", href: "https://console.cloud.google.com" },
            { label: "YouTube Studio — Aarav", sub: "Manage Aarav's channel", href: "https://studio.youtube.com" },
            { label: "YouTube Studio — Aarohi", sub: "Manage Aarohi's channel", href: "https://studio.youtube.com" },
            { label: "API Docs", sub: "Local FastAPI docs", href: "http://localhost:8000/docs" },
          ].map((link) => (
            <a
              key={link.label}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-xl border border-white/10 bg-white/5 p-3 hover:bg-white/10 transition-colors block"
            >
              <p className="text-sm text-white">{link.label}</p>
              <p className="text-[10px] text-gray-500 mt-0.5">{link.sub}</p>
            </a>
          ))}
        </div>
      </div>
    </main>
  );
}
