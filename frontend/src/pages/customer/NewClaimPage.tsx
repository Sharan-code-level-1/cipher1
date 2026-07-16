import { FormEvent, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Camera, CheckCircle2, CloudUpload, LoaderCircle, X } from "lucide-react";
import { api } from "@/api/client";
import type { Vehicle } from "@/types";

const MAX_FILES = 5;
const MAX_SIZE_BYTES = 5 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function NewClaimPage() {
  const navigate = useNavigate();
  const { data: vehicles = [] } = useQuery({
    queryKey: ["vehicles"],
    queryFn: async () => (await api.get<Vehicle[]>("/vehicles")).data,
  });
  const [vehicleId, setVehicleId] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [incidentDate, setIncidentDate] = useState(new Date().toISOString().slice(0, 16));
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedVehicle = useMemo(
    () => vehicles.find((vehicle) => vehicle.id === vehicleId),
    [vehicles, vehicleId]
  );

  function chooseFiles(list: FileList | null) {
    setError("");
    if (!list) return;

    const incoming = Array.from(list);
    const next = [...files];

    for (const file of incoming) {
      if (next.length >= MAX_FILES) {
        setError(`Maximum ${MAX_FILES} images are allowed per claim.`);
        break;
      }
      if (!ACCEPTED_TYPES.includes(file.type)) {
        setError(`${file.name} is not a supported image type.`);
        continue;
      }
      if (file.size > MAX_SIZE_BYTES) {
        setError(`${file.name} exceeds the 5 MB upload limit.`);
        continue;
      }
      const duplicate = next.some(
        (existing) => existing.name === file.name && existing.size === file.size && existing.lastModified === file.lastModified
      );
      if (!duplicate) next.push(file);
    }

    setFiles(next);
  }

  function removeFile(index: number) {
    setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!vehicleId) {
      setError("Select a vehicle before submitting the claim.");
      return;
    }
    if (files.length === 0) {
      setError("Upload at least one damage photo before submitting.");
      return;
    }
    setLoading(true);
    setError("");
    setProgress("Creating claim draft…");
    try {
      const { data: claim } = await api.post("/claims", {
        vehicle_id: vehicleId,
        description,
        incident_location: location,
        incident_date: new Date(incidentDate).toISOString(),
      });

      for (const [index, file] of files.entries()) {
        setProgress(`Uploading evidence ${index + 1} of ${files.length}…`);
        const fd = new FormData();
        fd.append("file", file);
        await api.post(`/claims/${claim.id}/images`, fd);
      }

      setProgress("Submitting claim and starting AI analysis…");
      const submitted = await api.post(`/claims/${claim.id}/submit`);
      navigate(`/app/claims/${submitted.data.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || "Failed to create claim");
    } finally {
      setLoading(false);
      setProgress("");
    }
  }

  return (
    <div className="space-y-7">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-600 dark:text-blue-300">Customer workflow</p>
          <h1 className="page-title">File a new claim</h1>
          <p className="page-subtitle">
            Select the vehicle, describe the incident, upload evidence and submit it into the AI claim assessment pipeline.
          </p>
        </div>
        <div className="auth-pill w-fit">
          <CheckCircle2 size={14} />
          Draft → Evidence → Submit → AI processing
        </div>
      </div>

      <form className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]" onSubmit={onSubmit}>
        <div className="space-y-6">
          <section className="card space-y-5">
            <div>
              <h2 className="text-xl font-semibold tracking-[-0.03em]">Claim details</h2>
              <p className="mt-1 text-sm text-slate-500">These fields keep the backend request exactly aligned with the current workflow.</p>
            </div>

            <div>
              <label className="label" htmlFor="vehicle">Vehicle</label>
              <select id="vehicle" className="input" value={vehicleId} onChange={(e) => setVehicleId(e.target.value)} required>
                <option value="">Select vehicle</option>
                {vehicles.map((v) => (
                  <option key={v.id} value={v.id}>{v.make} {v.model} ({v.registration_number})</option>
                ))}
              </select>
              {vehicles.length === 0 && <p className="mt-2 text-sm text-amber-600">No vehicles found. Add one under Vehicles first.</p>}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="label" htmlFor="location">Incident location</label>
                <input id="location" className="input" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Eg. Chennai, GST Road" />
              </div>
              <div>
                <label className="label" htmlFor="incident-date">Incident date</label>
                <input id="incident-date" type="datetime-local" className="input" value={incidentDate} onChange={(e) => setIncidentDate(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="label" htmlFor="desc">Description</label>
              <textarea id="desc" className="input min-h-32 rounded-[1.35rem]" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Describe what happened and which vehicle area appears damaged." />
            </div>
          </section>

          <section className="card space-y-4">
            <div>
              <h2 className="text-xl font-semibold tracking-[-0.03em]">Damage photos</h2>
              <p className="mt-1 text-sm text-slate-500">JPEG, PNG or WebP. Up to {MAX_FILES} photos, 5 MB each.</p>
            </div>

            <label htmlFor="images" className="flex cursor-pointer flex-col items-center justify-center rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50/70 px-6 py-10 text-center transition hover:border-blue-400 hover:bg-blue-50/50 dark:border-white/10 dark:bg-white/5 dark:hover:bg-blue-400/10">
              <CloudUpload className="mb-4 h-9 w-9 text-blue-600" />
              <span className="text-sm font-semibold text-slate-900 dark:text-white">Choose or drop vehicle evidence</span>
              <span className="mt-1 text-xs text-slate-500">The server will repeat security checks before storage.</span>
              <input id="images" type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(e) => chooseFiles(e.target.files)} className="sr-only" />
            </label>

            {files.length > 0 && (
              <div className="grid gap-3 sm:grid-cols-2">
                {files.map((file, index) => (
                  <div key={`${file.name}-${file.lastModified}`} className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white/70 p-3 dark:border-white/10 dark:bg-white/5">
                    <div className="grid h-11 w-11 place-items-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-400/10 dark:text-blue-300">
                      <Camera size={18} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-semibold">{file.name}</div>
                      <div className="text-xs text-slate-500">{(file.size / 1024).toFixed(0)} KB</div>
                    </div>
                    <button type="button" className="grid h-8 w-8 place-items-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-white/10 dark:hover:text-white" onClick={() => removeFile(index)} aria-label={`Remove ${file.name}`}>
                      <X size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <aside className="space-y-6">
          <section className="card sticky top-24 space-y-5">
            <div>
              <h2 className="text-xl font-semibold tracking-[-0.03em]">Submission review</h2>
              <p className="mt-1 text-sm text-slate-500">Confirm the core details before this enters automated assessment.</p>
            </div>

            <div className="space-y-3 text-sm">
              <ReviewRow label="Vehicle" value={selectedVehicle ? `${selectedVehicle.make} ${selectedVehicle.model}` : "Not selected"} />
              <ReviewRow label="Location" value={location || "Not provided"} />
              <ReviewRow label="Incident" value={incidentDate ? new Date(incidentDate).toLocaleString() : "Not provided"} />
              <ReviewRow label="Photos" value={`${files.length} selected`} />
            </div>

            <div className="rounded-[1.25rem] bg-slate-50 p-4 text-sm leading-6 text-slate-600 dark:bg-white/5 dark:text-slate-300">
              <div className="mb-2 flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
                <AlertCircle size={16} />
                Workflow note
              </div>
              The backend will create the draft, store validated images, submit the claim, and start AI processing exactly as the baseline flow defines.
            </div>

            {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-200">{error}</div>}
            {progress && <div className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-400/20 dark:bg-blue-400/10 dark:text-blue-200">{progress}</div>}

            <button className="btn-primary w-full" disabled={loading}>
              {loading ? (
                <>
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                  Submitting claim
                </>
              ) : (
                "Submit claim"
              )}
            </button>
          </section>
        </aside>
      </form>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 rounded-2xl bg-slate-50/80 px-4 py-3 dark:bg-white/5">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-semibold text-slate-900 dark:text-white">{value}</span>
    </div>
  );
}
