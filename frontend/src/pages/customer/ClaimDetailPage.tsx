import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, FileImage, LoaderCircle, ShieldAlert } from "lucide-react";
import { api } from "@/api/client";
import type { Claim } from "@/types";
import { formatCurrency, formatDate, severityColor, statusColor } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { useState } from "react";

export default function ClaimDetailPage() {
  const { id } = useParams();
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const [amount, setAmount] = useState("");

  const { data: claim, isLoading, isError } = useQuery({
    queryKey: ["claim", id],
    queryFn: async () => (await api.get<Claim>(`/claims/${id}`)).data,
    enabled: !!id,
  });

  const statusMut = useMutation({
    mutationFn: async (status: string) =>
      api.patch(`/claims/${id}/status`, {
        status,
        note,
        approved_amount: amount ? Number(amount) : undefined,
        rejection_reason: status === "rejected" ? note : undefined,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["claim", id] }),
  });

  if (isLoading) return <p className="text-slate-500">Loading claim…</p>;
  if (isError || !claim) return <p className="text-red-600">Unable to load claim.</p>;

  const detection = claim.detections?.[0];
  const cost = claim.cost_estimates?.[0];
  const fraud = claim.fraud_assessments?.[0];
  const canReview = user && ["surveyor", "fraud_analyst", "admin", "super_admin", "insurance_officer"].includes(user.role);

  return (
    <div className="space-y-7">
      <section className="relative overflow-hidden rounded-[2rem] bg-slate-950 p-7 text-white shadow-[0_24px_90px_rgba(15,23,42,0.18)]">
        <div className="absolute -right-16 -top-20 h-64 w-64 rounded-full bg-blue-500/30 blur-3xl" />
        <div className="relative z-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold text-blue-200">Claim detail</p>
            <h1 className="mt-2 font-display text-5xl font-semibold leading-none tracking-[-0.06em]">{claim.claim_number}</h1>
            <div className="mt-5 flex flex-wrap gap-2">
              <span className={`badge ${statusColor(claim.status)}`}>{claim.status}</span>
              {claim.severity && <span className={`badge ${severityColor(claim.severity)}`}>{claim.severity}</span>}
              {claim.fraud_score != null && <span className="badge bg-amber-100 text-amber-900">Fraud score {claim.fraud_score}</span>}
            </div>
          </div>
          <div className="text-sm text-slate-300">Updated {formatDate(claim.updated_at)}</div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="card space-y-5">
          <div>
            <h2 className="text-xl font-semibold tracking-[-0.03em]">Incident and evidence</h2>
            <p className="mt-1 text-sm text-slate-500">Vehicle evidence uploaded by the customer.</p>
          </div>
          <p className="rounded-[1.25rem] bg-slate-50/80 p-4 text-sm leading-6 text-slate-600 dark:bg-white/5 dark:text-slate-300">
            {claim.description || "No description provided."}
          </p>
          <div className="grid gap-3 text-sm sm:grid-cols-2">
            <Info label="Location" value={claim.incident_location || "—"} />
            <Info label="Incident date" value={formatDate(claim.incident_date)} />
          </div>
          <div>
            <div className="mb-3 text-sm font-semibold">Images ({claim.images?.length || 0})</div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {(claim.images || []).map((img) => (
                <div key={img.id} className="rounded-[1.25rem] border border-slate-200 bg-white/70 p-4 text-xs dark:border-white/10 dark:bg-white/5">
                  <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-400/10 dark:text-blue-300">
                    <FileImage size={18} />
                  </div>
                  <div className="truncate font-semibold text-slate-900 dark:text-white">{img.original_filename}</div>
                  <div className="mt-1 text-slate-500">{img.width}×{img.height} · {(img.size_bytes / 1024).toFixed(0)} KB</div>
                  <div className="mt-1 truncate text-slate-400">{img.sha256.slice(0, 12)}…</div>
                </div>
              ))}
              {(claim.images || []).length === 0 && <p className="text-sm text-slate-500">No images attached.</p>}
            </div>
          </div>
        </section>

        <aside className="space-y-6">
          <section className="card">
            <h2 className="text-xl font-semibold tracking-[-0.03em]">Cost estimate</h2>
            {cost ? (
              <div className="mt-4 space-y-2 text-sm">
                <CostRow label="Parts" value={formatCurrency(cost.parts_total)} />
                <CostRow label="Labour" value={formatCurrency(cost.labour_total)} />
                <CostRow label="Painting" value={formatCurrency(cost.painting_total)} />
                <CostRow label="Taxes" value={formatCurrency(cost.taxes_total)} />
                <div className="mt-3 flex justify-between rounded-2xl bg-slate-950 px-4 py-3 font-semibold text-white dark:bg-white dark:text-slate-950">
                  <span>Total</span><span>{formatCurrency(cost.grand_total)}</span>
                </div>
                <div className="text-slate-500">Repair time ~ {cost.repair_days} day(s)</div>
              </div>
            ) : <p className="mt-4 text-sm text-slate-500">Not available yet</p>}
          </section>

          {canReview && claim.status === "surveyor_review" && (
            <section className="card space-y-4">
              <h2 className="text-xl font-semibold tracking-[-0.03em]">Surveyor actions</h2>
              <textarea className="input min-h-24 rounded-[1.25rem]" placeholder="Inspection notes" value={note} onChange={(e) => setNote(e.target.value)} />
              <input className="input" placeholder="Approved amount" value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="numeric" />
              {statusMut.isError && <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-400/10 dark:text-red-200">Status update failed.</div>}
              <div className="flex gap-2">
                <button className="btn-primary flex-1" onClick={() => statusMut.mutate("approved")} disabled={statusMut.isPending}>{statusMut.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <CheckCircle2 size={16} />} Approve</button>
                <button className="btn-danger flex-1" onClick={() => statusMut.mutate("rejected")} disabled={statusMut.isPending}>Reject</button>
              </div>
            </section>
          )}
        </aside>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="card">
          <h2 className="text-xl font-semibold tracking-[-0.03em]">AI damage detection</h2>
          {detection ? (
            <div className="mt-4 space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <Info label="Confidence" value={`${(detection.confidence * 100).toFixed(1)}%`} />
                <Info label="Area" value={`${detection.damage_area_pct}%`} />
              </div>
              <p className="rounded-[1.25rem] bg-slate-50/80 p-4 leading-6 text-slate-600 dark:bg-white/5 dark:text-slate-300">{detection.explanation?.reason}</p>
              <div className="space-y-2">
                {(detection.damages || []).map((d: any, i: number) => (
                  <div key={i} className="flex justify-between gap-3 rounded-2xl border border-slate-200 bg-white/70 px-4 py-3 dark:border-white/10 dark:bg-white/5">
                    <span className="font-semibold">{d.part} — {d.type}</span>
                    <span className="text-slate-500">{(d.confidence * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
              <div className="text-slate-500">Repair: {detection.explanation?.repair_explanation}</div>
            </div>
          ) : <p className="mt-4 text-sm text-slate-500">No detection yet</p>}
        </section>

        <section className="card">
          <h2 className="text-xl font-semibold tracking-[-0.03em]">Evidence-risk assessment</h2>
          {fraud ? (
            <div className="mt-4 space-y-4 text-sm">
              <div className="flex items-center gap-4 rounded-[1.4rem] bg-amber-50 p-4 text-amber-950 dark:bg-amber-400/10 dark:text-amber-100">
                <ShieldAlert size={24} />
                <div>
                  <div className="text-2xl font-semibold tracking-[-0.04em]">{fraud.risk_score}</div>
                  <div className="capitalize">{fraud.risk_level} risk</div>
                </div>
              </div>
              <p className="leading-6 text-slate-600 dark:text-slate-300">{fraud.summary}</p>
              <div className="space-y-2">
                {(fraud.signals || []).map((s) => (
                  <div key={s.id} className="rounded-2xl bg-slate-50/80 p-3 dark:bg-white/5">
                    <div className="flex justify-between gap-2 font-semibold"><span>{s.signal_type}</span><span>w={s.weight}</span></div>
                    <div className="mt-1 text-slate-600 dark:text-slate-300">{s.message}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="mt-4 flex gap-3 rounded-[1.25rem] bg-slate-50/80 p-4 text-sm text-slate-500 dark:bg-white/5">
              <AlertTriangle size={18} /> No fraud assessment yet
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-slate-50/80 px-4 py-3 dark:bg-white/5">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 font-semibold text-slate-900 dark:text-white">{value}</div>
    </div>
  );
}

function CostRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 rounded-2xl bg-slate-50/80 px-4 py-3 dark:bg-white/5">
      <span className="text-slate-500">{label}</span>
      <span className="font-semibold text-slate-900 dark:text-white">{value}</span>
    </div>
  );
}
