"use client";

import { Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import { en } from "@/lib/i18n/en";

const STORAGE_KEY = "autoria-theme";

/**
 * Light/dark switch. The initial class is set before paint by the inline
 * script in layout.tsx; icon visibility is pure CSS (dark: variant), so this
 * component needs no state and cannot mismatch on hydration.
 */
export function ThemeToggle() {
  function toggle() {
    const isDark = document.documentElement.classList.toggle("dark");
    try {
      localStorage.setItem(STORAGE_KEY, isDark ? "dark" : "light");
    } catch {
      /* storage unavailable (private mode) — theme still toggles for the session */
    }
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      aria-label={en.theme.toggle}
      title={en.theme.toggle}
    >
      <Moon className="dark:hidden" aria-hidden="true" />
      <Sun className="hidden dark:block" aria-hidden="true" />
    </Button>
  );
}
