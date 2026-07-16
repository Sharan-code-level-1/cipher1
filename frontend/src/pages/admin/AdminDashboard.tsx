import { useQuery } from "@tanstack/react-query";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar, Doughnut, Line } from "react-chartjs-2";
import { api } from "@/api/client";
import type { DashboardStats } from "@/types";
import { formatCurrency } from "@/lib/utils";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Tooltip,
  Legend
);

export default function AdminDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: async () => (await api.get<DashboardStats>("/admin/dashboard")).data,
  });

  if (isLoading || !data) return <p>Loading analytics…</p>;

  const monthlyLabels = data.monthly_claims.map((m) => m.month);
  const statusLabels = Object.keys(data.claims_by_status);
  const severityLabels = Object.keys(data.severity_distribution);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Enterprise dashboard</h1>
        <p className="text-sm text-slate-500">Live claim, fraud, and cost analytics</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Kpi label="Total claims" value={data.total_claims} />
        <Kpi label="Pending" value={data.pending_claims} />
        <Kpi label="Fraud cases" value={data.fraud_cases} />
        <Kpi label="Revenue" value={formatCurrency(data.revenue)} />
        <Kpi label="Approved" value={data.approved_claims} />
        <Kpi label="Rejected" value={data.rejected_claims} />
        <Kpi label="Avg claim cost" value={formatCurrency(data.average_claim_cost)} />
        <Kpi label="Avg processing (h)" value={data.average_processing_hours} />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card">
          <h2 className="font-semibold mb-3">Monthly claims</h2>
          <Bar
            data={{
              labels: monthlyLabels,
              datasets: [
                {
                  label: "Claims",
                  data: data.monthly_claims.map((m) => m.count),
                  backgroundColor: "#2563eb",
                },
              ],
            }}
            options={{ responsive: true, plugins: { legend: { display: false } } }}
          />
        </div>
        <div className="card">
          <h2 className="font-semibold mb-3">Fraud trend</h2>
          <Line
            data={{
              labels: data.fraud_trend.map((m) => m.month),
              datasets: [
                {
                  label: "High/critical fraud",
                  data: data.fraud_trend.map((m) => m.count),
                  borderColor: "#dc2626",
                  backgroundColor: "rgba(220,38,38,0.2)",
                  tension: 0.3,
                },
              ],
            }}
            options={{ responsive: true }}
          />
        </div>
        <div className="card">
          <h2 className="font-semibold mb-3">Claims by status</h2>
          <Doughnut
            data={{
              labels: statusLabels,
              datasets: [
                {
                  data: statusLabels.map((k) => data.claims_by_status[k]),
                  backgroundColor: [
                    "#94a3b8",
                    "#3b82f6",
                    "#6366f1",
                    "#f59e0b",
                    "#a855f7",
                    "#10b981",
                    "#ef4444",
                    "#06b6d4",
                    "#22c55e",
                    "#64748b",
                  ],
                },
              ],
            }}
          />
        </div>
        <div className="card">
          <h2 className="font-semibold mb-3">Severity distribution</h2>
          <Bar
            data={{
              labels: severityLabels,
              datasets: [
                {
                  label: "Count",
                  data: severityLabels.map((k) => data.severity_distribution[k]),
                  backgroundColor: "#0f766e",
                },
              ],
            }}
            options={{ indexAxis: "y", plugins: { legend: { display: false } } }}
          />
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold mb-3">Vehicle brand distribution</h2>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2 text-sm">
          {Object.entries(data.brand_distribution).map(([brand, count]) => (
            <div
              key={brand}
              className="flex justify-between rounded-lg bg-slate-50 dark:bg-slate-800/50 px-3 py-2"
            >
              <span>{brand}</span>
              <span className="font-medium">{count}</span>
            </div>
          ))}
          {Object.keys(data.brand_distribution).length === 0 && (
            <p className="text-slate-500">No brand data yet</p>
          )}
        </div>
      </div>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-xl font-semibold mt-1">{value}</div>
    </div>
  );
}
