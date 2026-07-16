import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Car, LoaderCircle, Plus } from "lucide-react";
import { api } from "@/api/client";
import type { Vehicle } from "@/types";

export default function VehiclesPage() {
  const qc = useQueryClient();
  const { data: vehicles = [], isLoading } = useQuery({
    queryKey: ["vehicles"],
    queryFn: async () => (await api.get<Vehicle[]>("/vehicles")).data,
  });
  const [form, setForm] = useState({
    vin: "",
    registration_number: "",
    make: "",
    model: "",
    year: new Date().getFullYear(),
    color: "",
  });

  const create = useMutation({
    mutationFn: async () => api.post("/vehicles", form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vehicles"] });
      setForm({ vin: "", registration_number: "", make: "", model: "", year: new Date().getFullYear(), color: "" });
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div className="space-y-7">
      <div>
        <h1 className="page-title">My vehicles</h1>
        <p className="page-subtitle">Vehicle ownership is used by the claim workflow to bind claims safely to the current customer.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <section className="space-y-4">
          {isLoading && <p className="text-sm text-slate-500">Loading vehicles…</p>}
          {!isLoading && vehicles.length === 0 && (
            <div className="card py-10 text-center">
              <Car className="mx-auto mb-3 h-9 w-9 text-blue-600" />
              <h2 className="text-xl font-semibold tracking-[-0.03em]">No vehicles yet</h2>
              <p className="mt-2 text-sm text-slate-500">Add a vehicle before filing a claim.</p>
            </div>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            {vehicles.map((v) => (
              <div key={v.id} className="metric-card">
                <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-full bg-slate-950 text-white dark:bg-white dark:text-slate-950">
                  <Car size={18} />
                </div>
                <div className="text-xl font-semibold tracking-[-0.04em] text-slate-950 dark:text-white">{v.make} {v.model}</div>
                <div className="mt-1 text-sm text-slate-500">{v.year} · {v.color || "Color not set"}</div>
                <div className="mt-5 grid gap-2 text-sm">
                  <Info label="Registration" value={v.registration_number} />
                  <Info label="VIN" value={v.vin} />
                </div>
              </div>
            ))}
          </div>
        </section>

        <form className="card h-fit space-y-4" onSubmit={onSubmit}>
          <div>
            <h2 className="text-xl font-semibold tracking-[-0.03em]">Add vehicle</h2>
            <p className="mt-1 text-sm text-slate-500">Keep these exact backend fields unchanged.</p>
          </div>
          {Object.entries(form).map(([k, v]) => (
            <div key={k}>
              <label className="label capitalize" htmlFor={k}>{k.replaceAll("_", " ")}</label>
              <input
                id={k}
                className="input"
                type={k === "year" ? "number" : "text"}
                value={v as any}
                onChange={(e) => setForm({ ...form, [k]: k === "year" ? Number(e.target.value) : e.target.value })}
                required={k !== "color"}
              />
            </div>
          ))}
          {create.isError && <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-400/10 dark:text-red-200">Unable to save vehicle.</div>}
          <button className="btn-primary w-full" disabled={create.isPending}>
            {create.isPending ? <><LoaderCircle className="h-4 w-4 animate-spin" /> Saving</> : <><Plus size={16} /> Save vehicle</>}
          </button>
        </form>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 rounded-2xl bg-slate-50/90 px-4 py-3 dark:bg-white/5">
      <span className="text-slate-500">{label}</span>
      <span className="truncate text-right font-semibold">{value}</span>
    </div>
  );
}
