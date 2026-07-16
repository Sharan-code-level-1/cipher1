import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Eye, EyeOff, LoaderCircle, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";
import type { TokenResponse, User } from "@/types";
import AuthPageShell from "@/components/auth/AuthPageShell";

export default function LoginPage() {
  const [email, setEmail] = useState("customer@autoclaim.ai");
  const [password, setPassword] = useState("Customer@12345!");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post<TokenResponse>("/auth/login", { email, password });
      setTokens(data.access_token, data.refresh_token);
      const me = await api.get<User>("/auth/me", {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      setUser(me.data);
      navigate("/");
    } catch (err: any) {
      logout();
      setError(err?.response?.data?.error?.message || "Login failed. Check the details and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthPageShell>
      <motion.div
        initial={{ opacity: 0, y: 18, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.48, ease: "easeOut" }}
        className="auth-card"
      >
        <div className="mb-8 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 lg:hidden">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-slate-950 text-sm font-bold text-white dark:bg-white dark:text-slate-950">
              AC
            </div>
            <div>
              <div className="text-sm font-semibold">AutoClaim AI</div>
              <div className="text-xs text-slate-500">Claim intelligence</div>
            </div>
          </div>
          <div className="auth-pill ml-auto">
            <ShieldCheck size={14} />
            Secure login
          </div>
        </div>

        <div className="mb-8">
          <p className="text-sm font-semibold text-blue-600 dark:text-blue-300">Claim workspace</p>
          <h1 className="mt-3 font-display text-5xl font-semibold leading-none tracking-[-0.065em] text-slate-950 dark:text-white sm:text-6xl">
            Sign in.
            <br />
            Review faster.
          </h1>
          <p className="mt-5 text-[15px] leading-7 text-slate-500 dark:text-slate-400">
            Access vehicle claims, AI assessments, fraud-risk signals, and human review queues from one clean workspace.
          </p>
        </div>

        <form onSubmit={onSubmit} className="space-y-5" noValidate>
          <div>
            <label className="auth-field-label" htmlFor="email">Email</label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
              <input
                id="email"
                type="email"
                autoComplete="username"
                className="auth-field"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@autoclaim.ai"
                required
              />
            </div>
          </div>

          <div>
            <label className="auth-field-label" htmlFor="password">Password</label>
            <div className="relative">
              <LockKeyhole className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                className="auth-field pr-12"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full text-slate-400 transition hover:bg-slate-950/5 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:bg-white/10 dark:hover:text-white"
                onClick={() => setShowPassword((current) => !current)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-200" role="alert">
              {error}
            </div>
          )}

          <button className="btn-primary w-full" disabled={loading}>
            {loading ? (
              <>
                <LoaderCircle className="h-4 w-4 animate-spin" />
                Signing in
              </>
            ) : (
              <>
                Continue
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>

        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-slate-200 dark:bg-white/10" />
          <span className="text-xs font-medium text-slate-400">New here?</span>
          <div className="h-px flex-1 bg-slate-200 dark:bg-white/10" />
        </div>

        <p className="text-center text-sm text-slate-500 dark:text-slate-400">
          Create a customer account{" "}
          <Link className="font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-300" to="/register">
            Register
          </Link>
        </p>

        <div className="mt-6 rounded-[1.25rem] border border-slate-200/80 bg-slate-50/80 p-4 text-xs leading-5 text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-400">
          <div className="font-semibold text-slate-700 dark:text-slate-200">Demo access</div>
          <div className="mt-1">customer@autoclaim.ai / Customer@12345!</div>
          <div>admin@autoclaim.ai / Admin@12345!</div>
          <div>surveyor@autoclaim.ai / Surveyor@12345!</div>
        </div>
      </motion.div>
    </AuthPageShell>
  );
}
