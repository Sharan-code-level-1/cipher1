import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, Plus } from "lucide-react";
import { api } from "@/api/client";
import type { Claim } from "@/types";
import { formatCurrency, formatDate, statusColor } from "@/lib/utils";

export default function ClaimsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["claims-all"],
    queryFn: async () => (await api.get("/claims", { params: { page_size: 50 } })).data,
  });
  const claims: Claim[] = data?.items || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="page-title">My claims</h1>
          <p className="page-subtitle">View claim status, evidence-risk score, estimated repair impact, and assessment progress.</p>
        </div>
        <Link to="/app/claims/new" className="btn-primary"><Plus size={16} /> New claim</Link>
      </div>
      <div className="table-shell">
        {isLoading ? (
          <p className="p-5 text-sm text-slate-500">Loading…</p>
        ) : isError ? (
          <p className="p-5 text-sm text-red-600">Unable to load claims.</p>
        ) : claims.length === 0 ? (
          <div className="p-10 text-center">
            <h2 className="text-xl font-semibold tracking-[-0.03em]">No claims yet</h2>
            <p className="mt-2 text-sm text-slate-500">Start with a vehicle and upload damage photos.</p>
            <Link to="/app/claims/new" className="btn-primary mt-5">Create claim <ArrowRight size={16} /></Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <th className="px-5 py-3">Number</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Fraud</th>
                  <th className="px-5 py-3">Cost</th>
                  <th className="px-5 py-3">Updated</th>
                </tr>
              </thead>
              <tbody>
                {claims.map((c) => (
                  <tr key={c.id} className="border-t border-slate-100 transition hover:bg-slate-50/70 dark:border-white/10 dark:hover:bg-white/5">
                    <td className="px-5 py-4"><Link to={`/app/claims/${c.id}`} className="font-semibold text-slate-950 hover:text-blue-600 dark:text-white">{c.claim_number}</Link></td>
                    <td className="px-5 py-4"><span className={`badge ${statusColor(c.status)}`}>{c.status}</span></td>
                    <td className="px-5 py-4">{c.fraud_score ?? "—"}</td>
                    <td className="px-5 py-4">{c.estimated_cost ? formatCurrency(c.estimated_cost) : "Not assessed"}</td>
                    <td className="px-5 py-4 text-slate-500">{formatDate(c.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
