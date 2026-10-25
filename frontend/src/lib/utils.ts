import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number, decimals: number = 1): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function formatConfidence(conf: number): {
  label: "High" | "Moderate" | "Low / Emerging";
  colorClass: string;
} {
  if (conf >= 0.75) {
    return { label: "High", colorClass: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" };
  } else if (conf >= 0.40) {
    return { label: "Moderate", colorClass: "text-amber-400 bg-amber-500/10 border-amber-500/30" };
  }
  return { label: "Low / Emerging", colorClass: "text-cyan-400 bg-cyan-500/10 border-cyan-500/30" };
}

export function formatDate(isoString: string | null | undefined): string {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

export function getSeverityStyle(severity: string): {
  badgeClass: string;
  dotClass: string;
} {
  switch (severity.toUpperCase()) {
    case "CRITICAL":
      return {
        badgeClass: "bg-red-500/15 text-red-400 border-red-500/30",
        dotClass: "bg-red-400",
      };
    case "HIGH":
      return {
        badgeClass: "bg-orange-500/15 text-orange-400 border-orange-500/30",
        dotClass: "bg-orange-400",
      };
    case "MEDIUM":
      return {
        badgeClass: "bg-amber-500/15 text-amber-400 border-amber-500/30",
        dotClass: "bg-amber-400",
      };
    case "LOW":
    default:
      return {
        badgeClass: "bg-blue-500/15 text-blue-400 border-blue-500/30",
        dotClass: "bg-blue-400",
      };
  }
}
