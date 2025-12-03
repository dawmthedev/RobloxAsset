"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function GalleryPage() {
  const router = useRouter();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/gallery?asset_type=prototype&status_filter=completed`);
        const data = await res.json();
        setItems(data.items ?? []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function handleDelete(id: number) {
    try {
      await fetch(`${API_BASE}/gallery/${id}`, { method: "DELETE" });
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch (err) {
      console.error(err);
    }
  }

  function handleGenerateFinal(id: number) {
    router.push(`/final?prototypeId=${id}`);
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 px-4 py-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Gallery — Prototypes</h1>
            <p className="text-sm text-slate-300">Browse saved Shap-E prototypes and send them to Meshy.</p>
          </div>
          <nav className="flex gap-2 text-xs">
            <a href="/2d" className="px-3 py-1 rounded-full bg-slate-900 border border-slate-700">
              2D
            </a>
            <a href="/prototype" className="px-3 py-1 rounded-full bg-slate-900 border border-slate-700">
              Prototype
            </a>
            <a href="/gallery" className="px-3 py-1 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30">
              Gallery
            </a>
            <a href="/final" className="px-3 py-1 rounded-full bg-slate-900 border border-slate-700">
              Final
            </a>
          </nav>
        </header>

        {loading && <p className="text-xs text-slate-400">Loading gallery...</p>}
        {!loading && items.length === 0 && (
          <p className="text-xs text-slate-400 border border-dashed border-slate-800 rounded-xl p-4">
            No prototypes saved yet. Generate a prototype and save it from the Prototype page.
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden flex flex-col text-xs"
            >
              {item.gif_url && (
                <div className="relative aspect-square bg-slate-950">
                  <img src={item.gif_url} alt={item.name} className="h-full w-full object-contain" />
                </div>
              )}
              <div className="p-3 space-y-2">
                <p className="font-medium text-slate-100 truncate" title={item.prompt}>
                  {item.name}
                </p>
                <p className="line-clamp-2 text-slate-400">{item.prompt}</p>
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => handleGenerateFinal(item.id)}
                    className="flex-1 inline-flex h-8 items-center justify-center rounded-full bg-sky-500 text-[11px] font-medium text-slate-950 hover:bg-sky-400 transition-colors"
                  >
                    Generate Final 3D
                  </button>
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="inline-flex h-8 items-center justify-center rounded-full bg-red-500/10 px-3 text-[11px] font-medium text-red-300 hover:bg-red-500/20 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
