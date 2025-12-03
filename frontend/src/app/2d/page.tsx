"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function TwoDPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [refinementNotes, setRefinementNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any[]>([]);

  async function handleGenerate() {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/generate/2d`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, refinement_notes: refinementNotes || undefined }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResults((prev) => [data, ...prev]);
    } catch (err: any) {
      setError(err.message ?? "Failed to generate image");
    } finally {
      setLoading(false);
    }
  }

  async function handleRefine(id: number, refinementText: string) {
    if (!refinementText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/refine/2d`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_id: id, refinement_text: refinementText }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResults((prev) => [data, ...prev]);
    } catch (err: any) {
      setError(err.message ?? "Failed to refine image");
    } finally {
      setLoading(false);
    }
  }

  function handleContinueToPrototype(imageId: number) {
    router.push(`/prototype?imageId=${imageId}`);
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 px-4 py-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Tier 1 — 2D Concept Generation</h1>
            <p className="text-sm text-slate-300">
              Enter a prompt to generate a clean product render (plain background, centered object).
            </p>
          </div>
          <nav className="flex gap-2 text-xs">
            <a href="/2d" className="px-3 py-1 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30">
              2D
            </a>
            <a href="/prototype" className="px-3 py-1 rounded-full bg-slate-900 border border-slate-700">
              Prototype
            </a>
            <a href="/gallery" className="px-3 py-1 rounded-full bg-slate-900 border border-slate-700">
              Gallery
            </a>
            <a href="/final" className="px-3 py-1 rounded-full bg-slate-900 border border-slate-700">
              Final
            </a>
          </nav>
        </header>

        <section className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] items-start">
          <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <label className="block text-xs font-medium text-slate-300 mb-1">Prompt</label>
            <textarea
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 resize-none h-28"
              placeholder="A sleek futuristic sword with glowing blue edges"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <label className="block text-xs font-medium text-slate-300 mt-3 mb-1">Refinement notes (optional)</label>
            <textarea
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-xs outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 resize-none h-16"
              placeholder="Make it more metallic, emphasize the blade edges, remove any background clutter"
              value={refinementNotes}
              onChange={(e) => setRefinementNotes(e.target.value)}
            />
            <button
              onClick={handleGenerate}
              disabled={loading || !prompt.trim()}
              className="mt-3 inline-flex h-10 items-center justify-center rounded-full bg-sky-500 px-6 text-sm font-medium text-slate-950 disabled:cursor-not-allowed disabled:opacity-60 hover:bg-sky-400 transition-colors"
            >
              {loading ? "Generating..." : "Generate 2D Concept"}
            </button>
            {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
          </div>

          <div className="space-y-3">
            <h2 className="text-sm font-medium text-slate-200">Generated concepts</h2>
            {results.length === 0 && (
              <p className="text-xs text-slate-400 border border-dashed border-slate-800 rounded-xl p-4">
                No images yet. Generate a concept and it will appear here.
              </p>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              {results.map((item) => (
                <TwoDCard key={item.id} item={item} onRefine={handleRefine} onContinue={handleContinueToPrototype} />
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function TwoDCard({
  item,
  onRefine,
  onContinue,
}: {
  item: any;
  onRefine: (id: number, refinementText: string) => void;
  onContinue: (id: number) => void;
}) {
  const [refineText, setRefineText] = useState("");

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden flex flex-col">
      {item.image_url && (
        <div className="relative aspect-square bg-slate-950">
          <img src={item.image_url} alt={item.name} className="h-full w-full object-contain" />
        </div>
      )}
      <div className="p-3 space-y-2 text-xs">
        <p className="font-medium text-slate-100 truncate" title={item.prompt}>
          {item.name ?? `Concept #${item.id}`}
        </p>
        <p className="line-clamp-2 text-slate-400">{item.prompt}</p>
        <textarea
          className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950/60 px-2 py-1 text-[11px] outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 resize-none h-14"
          placeholder="Refine this concept..."
          value={refineText}
          onChange={(e) => setRefineText(e.target.value)}
        />
        <div className="flex gap-2 mt-2">
          <button
            onClick={() => onRefine(item.id, refineText)}
            className="flex-1 inline-flex h-8 items-center justify-center rounded-full bg-slate-800 text-[11px] font-medium hover:bg-slate-700 transition-colors"
          >
            Apply Refinement
          </button>
          <button
            onClick={() => onContinue(item.id)}
            className="flex-1 inline-flex h-8 items-center justify-center rounded-full bg-sky-500 text-[11px] font-medium text-slate-950 hover:bg-sky-400 transition-colors"
          >
            Prototype →
          </button>
        </div>
      </div>
    </div>
  );
}
