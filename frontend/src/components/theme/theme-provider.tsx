"use client";

/**
 * DevTwin — Theme Provider
 *
 * Thin wrapper around `next-themes` providing Light / Dark / System theme
 * selection via a `.dark` class on <html>. Scoped intentionally to be a
 * global, low-risk addition: the authenticated dashboard currently uses
 * zero `dark:`-prefixed Tailwind utilities and zero theme CSS variables
 * (verified before adding this), so toggling the `.dark` class has no
 * visible effect there — only the marketing site and the login page
 * define `dark:` variants, so only they visually respond to this
 * provider. The dashboard's current (dark-only) appearance is unaffected
 * regardless of the selected theme.
 */

import { ThemeProvider as NextThemesProvider } from "next-themes";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      {children}
    </NextThemesProvider>
  );
}
