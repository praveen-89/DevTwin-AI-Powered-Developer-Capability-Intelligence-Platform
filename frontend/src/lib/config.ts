/**
 * DevTwin Frontend — Runtime Environment Configuration
 */

export const env = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL || "",
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "",
  isDev: process.env.NODE_ENV !== "production",
};
