import Link from "next/link";

export default function HomePage() {
  return (
    <main className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-white mb-2">Aarav AI Music</h1>
      <p className="text-gray-400 mb-8">AI Music Production Control Panel</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[
          { href: "/covers", label: "Cover Songs", desc: "Browse 800-song catalog, generate covers", color: "border-purple-500/40" },
          { href: "/songs", label: "Original Songs", desc: "Original song library + approval queue", color: "border-blue-500/40" },
          { href: "/pipeline", label: "Pipeline", desc: "Trigger generation + live job status", color: "border-green-500/40" },
          { href: "/publishing", label: "Publishing", desc: "Upload receipts + scheduled releases", color: "border-yellow-500/40" },
          { href: "/analytics", label: "Analytics", desc: "Views, revenue, audience insights", color: "border-orange-500/40" },
          { href: "/settings", label: "Settings", desc: "API keys + pipeline configuration", color: "border-gray-500/40" },
        ].map(({ href, label, desc, color }) => (
          <Link
            key={href}
            href={href}
            className={`rounded-xl border ${color} bg-white/5 p-5 hover:bg-white/10 transition-colors`}
          >
            <p className="font-semibold text-white">{label}</p>
            <p className="mt-1 text-xs text-gray-400">{desc}</p>
          </Link>
        ))}
      </div>
    </main>
  );
}
