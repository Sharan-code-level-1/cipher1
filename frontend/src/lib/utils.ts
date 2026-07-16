import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number, currency = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value || 0);
}

export function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

export function statusColor(status: string) {
  const map: Record<string, string> = {
    draft: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    submitted: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
    ai_processing: "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300",
    fraud_review: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300",
    surveyor_review: "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300",
    approved: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
    rejected: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
    payment_pending: "bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300",
    paid: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
    closed: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  };
  return map[status] || map.draft;
}

export function severityColor(sev?: string | null) {
  const map: Record<string, string> = {
    minor: "bg-emerald-100 text-emerald-800",
    moderate: "bg-yellow-100 text-yellow-900",
    major: "bg-orange-100 text-orange-900",
    critical: "bg-red-100 text-red-800",
    total_loss: "bg-rose-200 text-rose-900",
  };
  return map[sev || ""] || "bg-slate-100 text-slate-700";
}
