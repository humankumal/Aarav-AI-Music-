"use client";
import { useState } from "react";
import { approveJob, rejectJob } from "@/lib/api-client";

interface Props {
  jobId: string;
  songTitle: string;
  onDecision: (decision: "approved" | "rejected") => void;
}

export function ApprovalPanel({ jobId, songTitle, onDecision }: Props) {
  const [notes, setNotes] = useState("");
  const [state, setState] = useState<"idle" | "approving" | "rejecting" | "done">("idle");
  const [error, setError] = useState("");

  const handleApprove = async () => {
    setState("approving");
    setError("");
    try {
      await approveJob(jobId, notes || undefined);
      setState("done");
      onDecision("approved");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
      setState("idle");
    }
  };

  const handleReject = async () => {
    setState("rejecting");
    setError("");
    try {
      await rejectJob(jobId, notes || undefined);
      setState("done");
      onDecision("rejected");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reject failed");
      setState("idle");
    }
  };

  if (state === "done") {
    return (
      <p className="text-sm text-green-400 py-2">Decision recorded. Use Resume in Pipeline to publish.</p>
    );
  }

  return (
    <div className="space-y-3 rounded-xl border border-white/10 bg-white/5 p-4">
      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Review Decision</p>
      <p className="text-sm text-gray-300">{songTitle}</p>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Optional notes…"
        rows={2}
        className="w-full rounded bg-white/10 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 outline-none focus:ring-1 focus:ring-white/30 resize-none"
      />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="flex gap-2">
        <button
          onClick={handleApprove}
          disabled={state === "approving"}
          className="flex-1 rounded py-2 text-sm font-medium bg-green-800 hover:bg-green-700 text-white disabled:opacity-50 transition-colors"
        >
          {state === "approving" ? "Approving…" : "Approve"}
        </button>
        <button
          onClick={handleReject}
          disabled={state === "rejecting"}
          className="flex-1 rounded py-2 text-sm font-medium bg-red-900 hover:bg-red-800 text-white disabled:opacity-50 transition-colors"
        >
          {state === "rejecting" ? "Rejecting…" : "Reject"}
        </button>
      </div>
    </div>
  );
}
