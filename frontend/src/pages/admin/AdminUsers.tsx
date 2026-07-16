import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { User } from "@/types";

export default function AdminUsers() {
  const qc = useQueryClient();
  const { data: users = [] } = useQuery({
    queryKey: ["admin-users"],
    queryFn: async () => (await api.get<User[]>("/admin/users")).data,
  });
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    role: "customer",
  });

  const create = useMutation({
    mutationFn: async () => api.post("/admin/users", form),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">User management</h1>
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b dark:border-slate-800">
                <th className="py-2">Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b dark:border-slate-800">
                  <td className="py-3">{u.full_name}</td>
                  <td>{u.email}</td>
                  <td className="capitalize">{u.role.replaceAll("_", " ")}</td>
                  <td>{u.is_active ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <form className="card space-y-3 h-fit" onSubmit={onSubmit}>
          <h2 className="font-semibold">Create user</h2>
          <input
            className="input"
            placeholder="Full name"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            required
          />
          <input
            className="input"
            placeholder="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
          <input
            className="input"
            placeholder="Password"
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
          <select
            className="input"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          >
            {[
              "customer",
              "surveyor",
              "insurance_officer",
              "repair_workshop",
              "fraud_analyst",
              "admin",
            ].map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button className="btn-primary w-full">Create</button>
        </form>
      </div>
    </div>
  );
}
