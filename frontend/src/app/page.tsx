import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center px-4">
      <div className="max-w-3xl w-full space-y-10">
        <div className="space-y-3 text-center">
          <p className="text-sm uppercase tracking-[0.25em] text-sky-300">
            3D Asset Pipeline
          </p>
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-semibold tracking-tight">
            2D → Shap-E Prototype → Meshy Final Model
          </h1>
          <p className="text-slate-300 max-w-2xl mx-auto text-sm sm:text-base">
            Start by generating a clean 2D concept, then turn it into a 3D prototype and
            a final production‑ready Meshy model. Click below to open the 2D generator.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/2d"
            className="inline-flex h-11 items-center justify-center rounded-full bg-sky-500 px-8 text-sm font-medium text-slate-950 shadow-lg shadow-sky-500/30 hover:bg-sky-400 transition-colors"
          >
            Open 2D Generator
          </Link>
          <div className="flex gap-2 text-xs text-slate-400">
            <span>Then visit</span>
            <code className="rounded bg-slate-900/60 px-2 py-1">/prototype</code>
            <span>,</span>
            <code className="rounded bg-slate-900/60 px-2 py-1">/gallery</code>
            <span>and</span>
            <code className="rounded bg-slate-900/60 px-2 py-1">/final</code>
          </div>
        </div>
      </div>
    </div>
  );
}
