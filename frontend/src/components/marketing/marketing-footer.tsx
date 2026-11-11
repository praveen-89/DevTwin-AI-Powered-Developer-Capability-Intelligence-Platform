import Link from "next/link";
import { GitBranch } from "lucide-react";

export function MarketingFooter() {
  return (
    <footer className="border-t border-slate-800/60 bg-[#090d16]">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-10 md:flex-row md:items-start md:justify-between md:px-8">
        <div className="space-y-2">
          <div className="flex items-center gap-2.5">
            <div className="h-6 w-6 rounded-md bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center">
              <GitBranch className="h-3 w-3 text-cyan-400" aria-hidden="true" />
            </div>
            <span className="text-sm font-bold text-slate-100">DevTwin</span>
          </div>
          <p className="max-w-sm text-xs leading-relaxed text-slate-500">
            An AI-powered developer capability intelligence platform — a final-year
            engineering project built to turn repository evidence into an
            explainable capability profile.
          </p>
        </div>

        <nav className="flex gap-8 text-xs" aria-label="Footer navigation">
          <div className="flex flex-col gap-2">
            <span className="font-semibold text-slate-300">Product</span>
            <Link href="/" className="text-slate-500 hover:text-slate-300">Home</Link>
            <Link href="/how-it-works" className="text-slate-500 hover:text-slate-300">How it works</Link>
            <Link href="/about" className="text-slate-500 hover:text-slate-300">About</Link>
          </div>
          <div className="flex flex-col gap-2">
            <span className="font-semibold text-slate-300">Account</span>
            <Link href="/login" className="text-slate-500 hover:text-slate-300">Sign in</Link>
            <Link href="/signup" className="text-slate-500 hover:text-slate-300">Create account</Link>
          </div>
        </nav>
      </div>
      <div className="border-t border-slate-800/60 px-5 py-4 text-center text-[11px] text-slate-600 md:px-8">
        {/* A static year avoids Next.js's Cache Components restriction on
            reading the current time during prerendering (new Date()). */}
        &copy; 2026 DevTwin. Evidence-backed, not a generic GitHub dashboard.
      </div>
    </footer>
  );
}
