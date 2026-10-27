import { createClient, SupabaseClient } from "@supabase/supabase-js";

/**
 * DevTwin — Supabase Browser Client Singleton
 *
 * Credentials policy:
 * - Uses NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY only.
 * - NEVER uses or exposes SUPABASE_SERVICE_ROLE_KEY.
 * - If env vars are missing or placeholders, isSupabaseConfigured() returns false
 *   and auth operations present a clear configuration message without crashing.
 */

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();

export function isSupabaseConfigured(): boolean {
  if (!supabaseUrl || !supabaseAnonKey) return false;
  if (supabaseUrl.includes("your-project.supabase.co") || supabaseUrl.includes("[project-ref]")) {
    return false;
  }
  if (supabaseAnonKey.startsWith("eyJ") && supabaseAnonKey.endsWith("...")) {
    return false;
  }
  return true;
}

let supabaseInstance: SupabaseClient | null = null;

export function getSupabaseClient(): SupabaseClient | null {
  if (!isSupabaseConfigured()) {
    return null;
  }

  if (!supabaseInstance) {
    supabaseInstance = createClient(supabaseUrl!, supabaseAnonKey!, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });
  }

  return supabaseInstance;
}
