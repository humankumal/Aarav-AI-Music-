import { clsx } from "clsx";

interface Props {
  lyricsText: string;
}

const SECTION_COLORS: Record<string, string> = {
  VERSE: "text-blue-400",
  CHORUS: "text-purple-400",
  BRIDGE: "text-orange-400",
  OUTRO: "text-gray-400",
};

export function LyricsPreview({ lyricsText }: Props) {
  const lines = lyricsText.split("\n");
  return (
    <div className="font-mono text-sm leading-relaxed space-y-1">
      {lines.map((line, i) => {
        const sectionMatch = line.match(/^\[(.+?)\]$/);
        if (sectionMatch) {
          const section = sectionMatch[1].split(" ")[0];
          const color = SECTION_COLORS[section] ?? "text-gray-400";
          return (
            <p key={i} className={clsx("font-bold mt-3 uppercase tracking-widest text-xs", color)}>
              {line}
            </p>
          );
        }
        if (!line.trim()) return <p key={i} className="h-2" />;
        return <p key={i} className="text-gray-200">{line}</p>;
      })}
    </div>
  );
}
