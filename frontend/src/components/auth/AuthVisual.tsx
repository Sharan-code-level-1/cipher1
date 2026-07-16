import { motion } from "framer-motion";
import { CheckCircle2, FileSearch, ShieldCheck, Sparkles } from "lucide-react";

const stages = [
  "Evidence intake",
  "AI damage scan",
  "Fraud signal review",
  "Human decision",
];

export default function AuthVisual() {
  return (
    <section className="relative hidden min-h-screen overflow-hidden lg:flex lg:items-center lg:justify-center">
      <div className="absolute inset-0 apple-hero" />
      <div className="absolute left-10 top-8 z-20 flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-slate-950 text-sm font-bold text-white shadow-2xl shadow-slate-950/20">
          AC
        </div>
        <div>
          <div className="text-sm font-semibold text-slate-950">AutoClaim AI</div>
          <div className="text-xs text-slate-500">Claim intelligence platform</div>
        </div>
      </div>

      <div className="relative z-10 mx-auto flex w-full max-w-4xl flex-col items-center px-10 pt-16 text-center">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: "easeOut" }}
          className="auth-pill mb-6"
        >
          <Sparkles size={14} />
          Built for evidence-first insurance workflows
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08, duration: 0.65, ease: "easeOut" }}
          className="max-w-3xl font-display text-6xl font-semibold leading-[0.97] tracking-[-0.06em] text-slate-950 xl:text-7xl"
        >
          Claims made clearer.
          <br />
          Decisions made faster.
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.18, duration: 0.55, ease: "easeOut" }}
          className="mt-6 max-w-2xl text-lg leading-8 text-slate-600"
        >
          Upload vehicle evidence, assess visible damage, estimate repair impact, and route elevated-risk claims into human review.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 28 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.7, ease: "easeOut" }}
          className="relative mt-11 h-[360px] w-[620px]"
          aria-hidden="true"
        >
          <div className="absolute inset-x-16 bottom-2 h-24 rounded-[100%] bg-slate-900/10 blur-3xl" />

          <div className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full border border-slate-950/10 bg-white/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_32px_80px_rgba(15,23,42,0.12)] backdrop-blur-2xl [perspective:900px]">
            <div className="absolute inset-8 rounded-full border border-blue-500/20" style={{ animation: "orbit-spin 18s linear infinite" }} />
            <div className="absolute inset-16 rounded-full border border-slate-950/10" style={{ animation: "orbit-spin 26s linear infinite reverse" }} />
            <div className="absolute left-1/2 top-1/2 h-28 w-44 -translate-x-1/2 -translate-y-1/2 rounded-[2.4rem] bg-gradient-to-b from-slate-100 to-white shadow-[0_24px_60px_rgba(15,23,42,0.14)]" style={{ animation: "float-slow 5.5s ease-in-out infinite" }}>
              <div className="absolute left-8 top-9 h-9 w-28 rounded-t-[2rem] border border-slate-300 bg-slate-50" />
              <div className="absolute left-5 top-20 h-7 w-10 rounded-full bg-slate-950" />
              <div className="absolute right-5 top-20 h-7 w-10 rounded-full bg-slate-950" />
              <div className="absolute left-16 top-[5.3rem] h-3 w-16 rounded-full bg-blue-500/90" />
              <div className="absolute -right-8 top-10 grid h-16 w-16 place-items-center rounded-2xl bg-white shadow-xl shadow-slate-950/10">
                <ShieldCheck className="text-blue-600" size={24} />
              </div>
            </div>
            <div className="absolute inset-x-8 top-10 h-1 rounded-full bg-gradient-to-r from-transparent via-blue-500 to-transparent" style={{ animation: "scan-line 3.8s ease-in-out infinite" }} />
          </div>

          <FloatingCard className="left-1 top-20" icon={<FileSearch size={18} />} title="Damage scan" value="92%" />
          <FloatingCard className="right-0 top-28" icon={<ShieldCheck size={18} />} title="Risk level" value="Low" />
          <FloatingCard className="bottom-6 left-24" icon={<CheckCircle2 size={18} />} title="Review route" value="Surveyor" />
        </motion.div>
      </div>

      <div className="absolute bottom-8 left-10 right-10 z-20 grid grid-cols-4 gap-3">
        {stages.map((stage, index) => (
          <div key={stage} className="minimal-panel p-4 text-left">
            <div className="mb-2 text-xs font-semibold text-slate-400">0{index + 1}</div>
            <div className="text-sm font-semibold text-slate-900">{stage}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function FloatingCard({ className, icon, title, value }: { className: string; icon: React.ReactNode; title: string; value: string }) {
  return (
    <div className={`absolute min-w-40 rounded-[1.35rem] border border-white/80 bg-white p-4 text-left shadow-[0_20px_70px_rgba(15,23,42,0.10)] backdrop-blur-2xl ${className}`} style={{ animation: "soft-pulse 5s ease-in-out infinite" }}>
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-blue-50 text-blue-600">
        {icon}
      </div>
      <div className="text-xs font-medium text-slate-500">{title}</div>
      <div className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950">{value}</div>
    </div>
  );
}
