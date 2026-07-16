import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight, LoaderCircle } from "lucide-react";
import { api } from "@/api/client";
import AuthPageShell from "@/components/auth/AuthPageShell";

export default function RegisterPage() {
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    phone: "",
  });
  const [error, setError] = useState("");
  const [ok, setOk] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/auth/register", form);
      setOk(true);
      setTimeout(() => navigate("/login"), 1200);
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  const fields = [
    { key: "full_name", label: "Full name", type: "text", autoComplete: "name", required: true },
    { key: "email", label: "Email", type: "email", autoComplete: "email", required: true },
    { key: "phone", label: "Phone", type: "tel", autoComplete: "tel", required: false },
    { key: "password", label: "Password", type: "password", autoComplete: "new-password", required: true },
  ] as const;

  return (
    <AuthPageShell>
      <motion.div
        initial={{ opacity: 0, y: 18, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.48, ease: "easeOut" }}
        className="auth-card"
      >
        <div className="mb-8">
          <p className="text-sm font-semibold text-blue-600 dark:text-blue-300">Customer onboarding</p>
          <h1 className="mt-3 font-display text-5xl font-semibold leading-none tracking-[-0.065em] text-slate-950 dark:text-white sm:text-6xl">
            Start your
            <br />
            claim journey.
          </h1>
          <p className="mt-5 text-[15px] leading-7 text-slate-500 dark:text-slate-400">
            Register to add vehicles, submit damage photos, and track AI-assisted assessments.
          </p>
        </div>

        <form className="space-y-4" onSubmit={onSubmit}>
          {fields.map((field) => (
            <div key={field.key}>
              <label className="auth-field-label" htmlFor={field.key}>{field.label}</label>
              <input
                id={field.key}
                className="auth-field px-5"
                type={field.type}
                autoComplete={field.autoComplete}
                value={form[field.key]}
                onChange={(e) => setForm({ ...form, [field.key]: e.target.value })}
                required={field.required}
              />
            </div>
          ))}

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-200" role="alert">
              {error}
            </div>
          )}
          {ok && (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-200" role="status">
              Account created. Redirecting…
            </div>
          )}

          <button className="btn-primary w-full" disabled={loading || ok}>
            {loading ? (
              <>
                <LoaderCircle className="h-4 w-4 animate-spin" />
                Creating account
              </>
            ) : (
              <>
                Register
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>

        <Link to="/login" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-slate-500 transition hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-300">
          <ArrowLeft size={16} />
          Back to login
        </Link>
      </motion.div>
    </AuthPageShell>
  );
}
