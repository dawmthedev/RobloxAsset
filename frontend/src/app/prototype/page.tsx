"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function PrototypePage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const imageId = searchParams.get("imageId");

  const [image, setImage] = useState<any | null>(null);
  const [prototype, setPrototype] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!imageId) return;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/generate/2d/${imageId}`);
        if (!res.ok) throw new Error(await res.text());
        setImage(await res.json());
      } catch (err: any) {
        setError(err.message ?? "Failed to load image");
      }
    })();
  }, [imageId]);

  async function handleGeneratePrototype() {
    if (!imageId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/generate/shap_e`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_id: Number(imageId) }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setPrototype(data);
    } catch (err: any) {
      setError(err.message ?? "Failed to generate prototype");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveToGallery() {
    if (!prototype) return;
    try {
      await fetch(`${API_BASE}/gallery/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item_id: prototype.id, name: prototype.name }),
      });
      router.push("/gallery");
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 px-4 py-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Tier 2 — Shap-E Prototype</h1>
            <p className="text-sm text-slate-300">Generate a low-poly 3D prototype and GIF preview from your 2D concept.</p>
          </div>
          <nav className="flex gap-2 text-xs">
            <a href="/2d" className="px-3 py-1 rounded-full bg-slate-900 border border-slate-700">
              2D
            </a>
            <a href="/prototype" className="px-3 py-1 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30">
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

        <section className="grid gap-4 md:grid-cols-2 items-start">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
            <h2 className="text-sm font-medium text-slate-200">Selected 2D image</h2>
            {!image && <p className="text-xs text-slate-400">Pass ?imageId=123 in the URL from the 2D page.</p>}
            {image && (
              <>
                <div className="relative aspect-square bg-slate-950 rounded-xl overflow-hidden">
                  <img src={image.image_url} alt={image.name} className="h-full w-full object-contain" />
                </div>
                <p className="text-xs text-slate-300 line-clamp-2">{image.prompt}</p>
              </>
            )}
            <button
              onClick={handleGeneratePrototype}
              disabled={loading || !imageId}
              className="mt-2 inline-flex h-10 items-center justify-center rounded-full bg-sky-500 px-6 text-sm font-medium text-slate-950 disabled:cursor-not-allowed disabled:opacity-60 hover:bg-sky-400 transition-colors"
            >
              {loading ? "Generating prototype..." : "Generate Prototype (Shap-E)"}
            </button>
            {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
            <h2 className="text-sm font-medium text-slate-200">Prototype preview</h2>
            {!prototype && <p className="text-xs text-slate-400">No prototype yet. Generate one to see the GIF and mesh preview.</p>}
            {prototype && (
              <>
                {prototype.gif_url && (
                  <div className="relative aspect-square bg-slate-950 rounded-xl overflow-hidden">
                    <img src={prototype.gif_url} alt={prototype.name} className="h-full w-full object-contain" />
                  </div>
                )}
                <p className="text-xs text-slate-300">OBJ path: {prototype.obj_url ?? "pending"}</p>
                <button
                  onClick={handleSaveToGallery}
                  className="mt-2 inline-flex h-9 items-center justify-center rounded-full bg-emerald-500 px-5 text-xs font-medium text-slate-950 hover:bg-emerald-400 transition-colors"
                >
                  Save Prototype to Gallery
                </button>
              </>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
