import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthPage } from "@/components/auth/auth-page";

export const metadata: Metadata = {
  title: "Create Account | DevTwin",
  description: "Create a DevTwin account with GitHub to start building your evidence-backed capability profile.",
};

// AuthPage reads useSearchParams() (for OAuth callback errors), which
// requires a <Suspense> boundary under Next.js 16's Cache Components model.
export default function SignupPage() {
  return (
    <Suspense>
      <AuthPage mode="signup" />
    </Suspense>
  );
}
