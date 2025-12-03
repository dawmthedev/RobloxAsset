"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function FinalPage() {
  const searchParams = useSearchParams();
  const prototypeId = searchParams.get("prototypeId");

  const [task, setTask] = useState<any | null>(null);
  const [model, setModel] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startTask() {
    if (!prototypeId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/generate/meshy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prototype_id: Number(prototypeId) }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setTask(data);
    } catch (err: any) {
      setError(err.message ?? "Failed to start Meshy task");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let interval: any;
    if (task?.task_id) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/generate/meshy/task/${task.task_id}`);
          if (!res.ok) return;
          const data = await res.json();
          setTask(data);
          if (data.status === "SUCCEEDED" || data.status === "FAILED") {
            clearInterval(interval);
          }
        } catch (err) {
          console.error(err);
        }
      }, 5000);
    }
    return () => interval && clearInterval(interval);
  }, [task?.task_id]);

  useEffect(() => {
    if (!task?.gallery_item_id) return;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/generate/meshy/${task.gallery_item_id}`);
        if (res.ok) {
          setModel(await res.json());
        }
      } catch (err) {
        console.error(err);
      }
    })();
  }, [task?.gallery_item_id, task?.status]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 px-4 py-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Tier 3 — Meshy Final Model</h1>
            <p className="text-sm text-slate-300">
              Generate a high‑quality OBJ/FBX model from a selected prototype.
            </p>
          </div>
          <nav className="flex gap-2 text-xs">
            <a href="/2d" className="px-3 py-1 rounded-full bg-slate-900 border border-slate-700">
              2D
            </a>
            <a href="/prototype" className="px-3 py-1 rounded-full bg-slate-900 border border-slate-700">
              Prototype
            </a>
            <a href="/gallery" className="px-3 py-1 rounded-full bg-slate-900 border border-slate-700">
              Gallery
            </a>
            <a href="/final" className="px-3 py-1 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30">
              Final
            </a>
          </nav>
        </header>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-4">
          {!prototypeId && (
            <p className="text-xs text-slate-400">
              Open this page from the Gallery using “Generate Final 3D Model” so the prototypeId is provided.
            </p>
          )}

          <button
            onClick={startTask}
            disabled={loading || !prototypeId}
            className="inline-flex h-10 items-center justify-center rounded-full bg-sky-500 px-6 text-sm font-medium text-slate-950 disabled:cursor-not-allowed disabled:opacity-60 hover:bg-sky-400 transition-colors"
          >
            {loading ? "Creating Meshy task..." : "Generate Final 3D Model"}
          </button>

          {error && <p className="text-xs text-red-400">{error}</p>}

          {task && (
            <div className="text-xs text-slate-300 space-y-1">
              <p>
                Task ID: <code className="bg-slate-950/70 px-1 py-0.5 rounded">{task.task_id}</code>
              </p>
              <p>Status: {task.status}</p>
              <p>Progress: {task.progress ?? 0}%</p>
              {task.error_message && <p className="text-red-400">{task.error_message}</p>}
            </div>
          )}

          {model && (
            <div className="mt-4 space-y-2 text-xs text-slate-200">
              <h2 className="text-sm font-medium">Downloads</h2>
              {model.obj_url && (
                <a
                  href={model.obj_url}
                  className="inline-flex h-8 items-center justify-center rounded-full bg-slate-800 px-4 text-[11px] font-medium hover:bg-slate-700"
                  download
                >
                  Download OBJ
                </a>
              )}
              {model.fbx_url && (
                <a
                  href={model.fbx_url}
                  className="inline-flex h-8 items-center justify-center rounded-full bg-slate-800 px-4 text-[11px] font-medium hover:bg-slate-700 ml-2"
                  download
                >
                  Download FBX
                </a>
              )}
              {model.texture_url && (
                <a
                  href={model.texture_url}
                  className="inline-flex h-8 items-center justify-center rounded-full bg-slate-800 px-4 text-[11px] font-medium hover:bg-slate-700 ml-2"
                  download
                >
                  Download Textures
                </a>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
