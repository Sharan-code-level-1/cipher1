import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, ShieldAlert } from "lucide-react";
import { api } from "@/api/client";
import type { Claim } from "@/types";
import { formatCurrency, formatDate, statusColor } from "@/lib/utils";

export default function SurveyorQueue() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["surveyor-claims"],
    queryFn: async () =>
      (await api.get("/claims", { params: { page_size: 50 } })).data as { items: Claim[]; total: number },
  });

  const items = (data?.items || []).filter((c) => ["surveyor_review", "fraud_review", "ai_processing", "submitted"].includes(c.status));
  const highRisk = items.filter((c) => (c.fraud_score ?? 0) >= 70).length;

  return (
    <div className="space-y-7">
      <section className="relative overflow-hidden rounded-[2rem] bg-white/90 p-7 shadow-[0_24px_90px_rgba(15,23,42,0.08)] dark:bg-slate-900/80">
        <div className="absolute -right-16 -top-20 h-60 w-60 rounded-full bg-amber-200/50 blur-3xl dark:bg-amber-500/10" />
        <div className="relative z-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold text-blue-600 dark:text-blue-300">Human review queue</p>
            <h1 className="page-title">Surveyor / Fraud queue</h1>
            <p className="page-subtitle">Review AI suggestions, verify evidence, and approve or reject claims with notes.</p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:min-w-72">
            <MiniMetric label="Pending" value={items.length} />
            <MiniMetric label="High risk" value={highRisk} />
          </div>
        </div>
      </section>

      <section className="table-shell">
        {isLoading ? (
          <p className="p-5 text-sm text-slate-500">Loading…</p>
        ) : isError ? (
          <p className="p-5 text-sm text-red-600">Unable to load queue.</p>
        ) : items.length === 0 ? (
          <div className="p-10 text-center">
            <ShieldAlert className="mx-auto mb-3 h-9 w-9 text-slate-400" />
            <h2 className="text-xl font-semibold tracking-[-0.03em]">No claims pending review</h2>
            <p className="mt-2 text-sm text-slate-500">The queue is clear for now.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <th className="px-5 py-3">Claim</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Severity</th>
                  <th className="px-5 py-3">Fraud</th>
                  <th className="px-5 py-3">Estimate</th>
                  <th className="px-5 py-3">Submitted</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {items.map((c) => (
                  <tr key={c.id} className="border-t border-slate-100 transition hover:bg-slate-50/70 dark:border-white/10 dark:hover:bg-white/5">
                    <td className="px-5 py-4"><Link className="font-semibold text-slate-950 hover:text-blue-600 dark:text-white" to={`/surveyor/claims/${c.id}`}>{c.claim_number}</Link></td>
                    <td className="px-5 py-4"><span className={`badge ${statusColor(c.status)}`}>{c.status}</span></td>
                    <td className="px-5 py-4 capitalize">{c.severity || "—"}</td>
                    <td className="px-5 py-4">{c.fraud_score ?? "—"}</td>
                    <td className="px-5 py-4">{c.estimated_cost ? formatCurrency(c.estimated_cost) : "Not assessed"}</td>
                    <td className="px-5 py-4 text-slate-500">{formatDate(c.submitted_at || c.created_at)}</td>
                    <td className="px-5 py-4"><Link to={`/surveyor/claims/${c.id}`} className="inline-flex items-center gap-1 text-sm font-semibold text-blue-600">Open <ArrowRight size={14} /></Link></td>
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

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[1.25rem] bg-slate-50/80 p-4 dark:bg-white/5">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold tracking-[-0.04em]">{value}</div>
    </div>
  );
}
