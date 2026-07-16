import type { ReactNode } from "react";
import AuthVisual from "./AuthVisual";

export default function AuthPageShell({ children }: { children: ReactNode }) {
  return (
    <main className="grid min-h-screen overflow-hidden bg-[#f5f5f7] text-slate-950 dark:bg-slate-950 dark:text-white lg:grid-cols-[1.18fr_0.82fr]">
      <AuthVisual />
      <section className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-8 sm:px-6 lg:px-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.95),transparent_18rem),linear-gradient(180deg,#fbfbfd,#f5f5f7)] dark:bg-[radial-gradient(circle_at_50%_0%,rgba(30,64,175,0.25),transparent_20rem),linear-gradient(180deg,#020617,#0f172a)]" />
        <div className="absolute -right-24 top-10 h-72 w-72 rounded-full bg-blue-200/40 blur-3xl dark:bg-blue-700/20" />
        <div className="absolute -bottom-24 left-0 h-72 w-72 rounded-full bg-slate-200/70 blur-3xl dark:bg-cyan-700/10" />
        <div className="relative z-10 w-full max-w-[430px]">{children}</div>
      </section>
    </main>
  );
}
