import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, ClipboardList, FilePlus2, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "@/api/client";
import type { Claim } from "@/types";
import { formatCurrency, formatDate, statusColor } from "@/lib/utils";

export default function CustomerDashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["claims"],
    queryFn: async () => (await api.get("/claims")).data as { items: Claim[]; total: number },
  });

  const claims = data?.items || [];
  const open = claims.filter((c) => !["closed", "rejected", "paid"].includes(c.status)).length;
  const latestCost = claims.find((c) => c.estimated_cost)?.estimated_cost;

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-[2.25rem] bg-slate-950 p-8 text-white shadow-[0_30px_100px_rgba(15,23,42,0.18)] md:p-10">
        <div className="absolute -right-16 -top-24 h-72 w-72 rounded-full bg-blue-500/30 blur-3xl" />
        <div className="absolute bottom-0 right-10 hidden h-44 w-44 rounded-full border border-white/10 md:block" />
        <div className="relative z-10 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="auth-pill mb-5 border-white/10 bg-white/10 text-white">
              <Sparkles size={14} />
              Evidence intelligence workspace
            </div>
            <h1 className="max-w-3xl font-display text-5xl font-semibold leading-[0.95] tracking-[-0.065em] md:text-6xl">
              Track every claim from evidence to review.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-slate-300">
              Start a vehicle claim, upload damage photos, and follow the AI assessment and human review flow.
            </p>
          </div>
          <Link to="/app/claims/new" className="btn-primary bg-white text-slate-950 hover:bg-slate-100">
            New claim <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat icon={<ClipboardList size={18} />} title="Total claims" value={data?.total ?? 0} />
        <Stat icon={<ShieldCheck size={18} />} title="Open claims" value={open} />
        <Stat icon={<FilePlus2 size={18} />} title="Latest estimate" value={latestCost ? formatCurrency(latestCost) : "Not assessed"} />
      </div>

      <section className="table-shell">
        <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-5 py-4 dark:border-white/10">
          <div>
            <h2 className="text-lg font-semibold tracking-[-0.03em]">Recent claims</h2>
            <p className="text-sm text-slate-500">Latest submitted and assessed claims</p>
          </div>
          <Link to="/app/claims" className="text-sm font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-300">
            View all
          </Link>
        </div>
        {isLoading && <p className="p-5 text-sm text-slate-500">Loading…</p>}
        {isError && <p className="p-5 text-sm text-red-600">Unable to load claims.</p>}
        {!isLoading && !isError && claims.length === 0 && (
          <div className="p-8 text-center text-sm text-slate-500">No claims yet. File your first claim.</div>
        )}
        {claims.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <th className="px-5 py-3">Claim</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Severity</th>
                  <th className="px-5 py-3">Estimate</th>
                  <th className="px-5 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {claims.slice(0, 8).map((c) => (
                  <tr key={c.id} className="border-t border-slate-100 transition hover:bg-slate-50/70 dark:border-white/10 dark:hover:bg-white/5">
                    <td className="px-5 py-4">
                      <Link className="font-semibold text-slate-950 hover:text-blue-600 dark:text-white" to={`/app/claims/${c.id}`}>
                        {c.claim_number}
                      </Link>
                    </td>
                    <td className="px-5 py-4"><span className={`badge ${statusColor(c.status)}`}>{c.status}</span></td>
                    <td className="px-5 py-4 capitalize">{c.severity || "—"}</td>
                    <td className="px-5 py-4">{c.estimated_cost ? formatCurrency(c.estimated_cost) : "Not assessed"}</td>
                    <td className="px-5 py-4 text-slate-500">{formatDate(c.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({ title, value, icon }: { title: string; value: string | number; icon: React.ReactNode }) {
  return (
    <div className="metric-card">
      <div className="mb-5 flex h-10 w-10 items-center justify-center rounded-full bg-blue-50 text-blue-600 dark:bg-blue-400/10 dark:text-blue-300">{icon}</div>
      <div className="text-sm font-medium text-slate-500">{title}</div>
      <div className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-950 dark:text-white">{value}</div>
    </div>
  );
}
