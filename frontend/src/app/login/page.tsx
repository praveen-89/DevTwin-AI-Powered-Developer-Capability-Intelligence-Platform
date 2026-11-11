import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthPage } from "@/components/auth/auth-page";

export const metadata: Metadata = {
  title: "Sign In | DevTwin",
  description: "Sign in to DevTwin with GitHub to view your evidence-backed capability dashboard.",
};

// AuthPage reads useSearchParams() (for OAuth callback errors), which
// requires a <Suspense> boundary under Next.js 16's Cache Components model.
export default function LoginPage() {
  return (
    <Suspense>
      <AuthPage mode="login" />
    </Suspense>
  );
}
