import Link from "next/link";
export default function SongsPage() {
  return (
    <main className="p-8 max-w-5xl mx-auto">
      <Link href="/" className="text-xs text-gray-500 hover:text-gray-300">← Dashboard</Link>
      <h1 className="text-2xl font-bold text-white mt-2">Original Songs</h1>
      <p className="text-sm text-gray-400 mt-1">Song library coming in Sprint 5</p>
    </main>
  );
}
