import Link from "next/link";

export default function CoversPage() {
  return (
    <main className="p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <Link href="/" className="text-xs text-gray-500 hover:text-gray-300">← Dashboard</Link>
        <h1 className="text-2xl font-bold text-white mt-2">Cover Songs</h1>
        <p className="text-sm text-gray-400 mt-1">
          800 reference songs — Aarav & Aarohi reinterpret the emotional DNA as original compositions
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-8">
        <Link
          href="/covers/nepali"
          className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#1a1a2e] to-[#16213e] p-8 hover:border-white/30 transition-all group"
        >
          <p className="text-4xl font-bold text-white">400</p>
          <p className="text-sm text-gray-400 mt-1">Nepali Songs</p>
          <p className="text-xs text-gray-500 mt-3">
            Narayan Gopal, Aruna Lama, Sabin Rai, Swoopna Suman, Bartika Eam Rai + 15 more
          </p>
          <p className="mt-4 text-xs text-[#e94560] group-hover:underline">Browse catalog →</p>
        </Link>
        <Link
          href="/covers/global"
          className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#16213e] to-[#0f3460] p-8 hover:border-white/30 transition-all group"
        >
          <p className="text-4xl font-bold text-white">400</p>
          <p className="text-sm text-gray-400 mt-1">Global Songs</p>
          <p className="text-xs text-gray-500 mt-3">
            Michael Jackson, Adele, Taylor Swift, BTS, Arijit Singh, Lata Mangeshkar + 14 more
          </p>
          <p className="mt-4 text-xs text-[#e94560] group-hover:underline">Browse catalog →</p>
        </Link>
      </div>
    </main>
  );
}
