import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Car,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Search,
  Shield,
  Sun,
  Users,
  X,
} from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import { useThemeStore } from "@/stores/theme";
import { useState } from "react";
import { api } from "@/api/client";

export default function AppShell() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const { dark, toggle } = useThemeStore();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any>(null);
  const [searchError, setSearchError] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);

  const isAdmin = user && ["admin", "super_admin", "insurance_officer"].includes(user.role);
  const isSurveyor = user && ["surveyor", "fraud_analyst", "admin", "super_admin"].includes(user.role);
  const isCustomer = user?.role === "customer";
  const base = isAdmin ? "/admin" : isSurveyor && !isCustomer ? "/surveyor" : "/app";

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearchError("");
    if (q.trim().length < 2) return;
    try {
      const { data } = await api.get("/search", { params: { q } });
      setResults(data);
    } catch (err: any) {
      setResults(null);
      setSearchError(err?.response?.data?.error?.message || "Search failed. Try again.");
    }
  }

  async function signOut() {
    try {
      await api.post("/auth/logout");
    } catch {
      // Local sign-out must still happen even if the server session is already expired.
    } finally {
      logout();
      navigate("/login");
    }
  }

  const nav = (
    <>
      <NavItem to={base} end icon={<LayoutDashboard size={18} />} label="Dashboard" onClick={() => setMobileOpen(false)} />
      {isCustomer && (
        <>
          <NavItem to="/app/claims" icon={<ClipboardList size={18} />} label="Claims" onClick={() => setMobileOpen(false)} />
          <NavItem to="/app/vehicles" icon={<Car size={18} />} label="Vehicles" onClick={() => setMobileOpen(false)} />
        </>
      )}
      {isSurveyor && !isAdmin && (
        <NavItem to="/surveyor" end icon={<ClipboardList size={18} />} label="Queue" onClick={() => setMobileOpen(false)} />
      )}
      {isAdmin && (
        <>
          <NavItem to="/admin/users" icon={<Users size={18} />} label="Users" onClick={() => setMobileOpen(false)} />
          <NavItem to="/admin/audit" icon={<Shield size={18} />} label="Audit Logs" onClick={() => setMobileOpen(false)} />
        </>
      )}
    </>
  );

  return (
    <div className="min-h-screen bg-[#f5f5f7] text-slate-950 dark:bg-slate-950 dark:text-slate-100">
      <aside className="fixed inset-y-3 left-3 z-40 hidden w-72 flex-col rounded-[2rem] border border-white/70 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur-2xl dark:border-white/10 dark:bg-slate-900/80 lg:flex" aria-label="Main navigation">
        <BrandBlock userRole={user?.role} />
        <nav className="flex-1 space-y-1 p-3">{nav}</nav>
        <div className="p-4">
          <div className="rounded-[1.3rem] bg-slate-50/80 p-4 dark:bg-white/5">
            <div className="truncate text-sm font-semibold">{user?.full_name}</div>
            <div className="mb-3 truncate text-xs text-slate-500">{user?.email}</div>
            <button className="btn-secondary w-full" onClick={signOut}>
              <LogOut size={16} /> Sign out
            </button>
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/35 backdrop-blur-sm lg:hidden" onClick={() => setMobileOpen(false)}>
          <aside className="m-3 flex max-h-[calc(100vh-1.5rem)] w-[min(21rem,calc(100vw-1.5rem))] flex-col rounded-[2rem] border border-white/70 bg-white/95 shadow-2xl dark:border-white/10 dark:bg-slate-900/95" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between pr-4">
              <BrandBlock userRole={user?.role} />
              <button className="btn-secondary h-10 w-10 px-0" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
                <X size={18} />
              </button>
            </div>
            <nav className="flex-1 space-y-1 p-3">{nav}</nav>
            <div className="p-4">
              <button className="btn-secondary w-full" onClick={signOut}>
                <LogOut size={16} /> Sign out
              </button>
            </div>
          </aside>
        </div>
      )}

      <div className="min-h-screen lg:pl-[19.5rem]">
        <header className="sticky top-0 z-30 border-b border-white/70 bg-[#f5f5f7]/80 backdrop-blur-2xl dark:border-white/10 dark:bg-slate-950/80">
          <div className="flex items-center gap-3 px-4 py-3 md:px-6">
            <button className="btn-secondary h-11 w-11 px-0 lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
              <Menu size={18} />
            </button>
            <form onSubmit={onSearch} className="relative max-w-2xl flex-1">
              <label htmlFor="global-search" className="sr-only">Global search</label>
              <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                id="global-search"
                className="input rounded-full pl-11"
                placeholder="Search claims, VIN, policy, users..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </form>
            <button className="btn-secondary h-11 w-11 px-0" onClick={toggle} aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}>
              {dark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>
          {(results || searchError) && (
            <div className="px-4 pb-3 md:px-6">
              <div className="card text-sm">
                <div className="mb-3 flex justify-between gap-3">
                  <span className="font-semibold">Search results</span>
                  <button className="text-slate-500 hover:text-slate-900 dark:hover:text-white" onClick={() => { setResults(null); setSearchError(""); }}>
                    Close
                  </button>
                </div>
                {searchError ? (
                  <div className="rounded-2xl bg-red-50 px-4 py-3 text-red-700 dark:bg-red-400/10 dark:text-red-200">{searchError}</div>
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    {(["claims", "vehicles", "users", "policies"] as const).map((k) => (
                      <div key={k} className="rounded-2xl bg-slate-50/80 p-3 dark:bg-white/5">
                        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{k}</div>
                        {(results?.[k] || []).length === 0 && <div className="text-slate-400">None</div>}
                        {(results?.[k] || []).slice(0, 5).map((item: any) => (
                          <div key={item.id} className="truncate py-1 text-slate-700 dark:text-slate-300">
                            {item.claim_number || item.vin || item.email || item.policy_number}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </header>
        <main className="mx-auto max-w-[1440px] p-4 md:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function BrandBlock({ userRole }: { userRole?: string }) {
  return (
    <div className="px-5 py-5">
      <div className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-2xl bg-slate-950 text-sm font-bold text-white shadow-lg shadow-slate-950/15 dark:bg-white dark:text-slate-950">AC</div>
        <div>
          <div className="font-semibold leading-tight tracking-[-0.03em]">AutoClaim AI</div>
          <div className="text-xs capitalize text-slate-500">{userRole?.replace("_", " ")}</div>
        </div>
      </div>
    </div>
  );
}

function NavItem({ to, icon, label, end, onClick }: { to: string; icon: React.ReactNode; label: string; end?: boolean; onClick?: () => void }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        `flex min-h-12 items-center gap-3 rounded-2xl px-4 text-sm font-semibold transition ${
          isActive
            ? "bg-slate-950 text-white shadow-lg shadow-slate-950/10 dark:bg-white dark:text-slate-950"
            : "text-slate-600 hover:bg-white hover:text-slate-950 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white"
        }`
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}
