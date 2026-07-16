import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { formatDate } from "@/lib/utils";

export default function AdminAudit() {
  const { data: logs = [] } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: async () => (await api.get("/admin/audit-logs", { params: { limit: 100 } })).data,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Audit trail</h1>
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b dark:border-slate-800">
              <th className="py-2">Time</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Resource</th>
              <th>Status</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l: any) => (
              <tr key={l.id} className="border-b dark:border-slate-800">
                <td className="py-3 whitespace-nowrap">{formatDate(l.created_at)}</td>
                <td>{l.actor_email || "system"}</td>
                <td>{l.action}</td>
                <td>
                  {l.resource_type}
                  {l.resource_id ? `:${String(l.resource_id).slice(0, 8)}` : ""}
                </td>
                <td>{l.status}</td>
                <td>{l.ip_address || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
