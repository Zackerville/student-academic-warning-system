"use client";

import { useI18nStore } from "@/lib/i18n";
import { cn } from "@/lib/utils";

type Variant = "light" | "dark";

interface Props {
  /**
   * "light" — for dark backgrounds (white text + transparent bg)
   * "dark" — for light backgrounds (dark text + bordered bg)
   */
  variant?: Variant;
  className?: string;
}

export default function LanguageToggle({ variant = "dark", className }: Props) {
  const { lang, setLang } = useI18nStore();

  const isLight = variant === "light";

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-md overflow-hidden text-xs font-medium border",
        isLight ? "border-white/30" : "border-input",
        className
      )}
    >
      {(["vi", "en"] as const).map((l) => {
        const active = lang === l;
        return (
          <button
            key={l}
            type="button"
            onClick={() => setLang(l)}
            className={cn(
              "px-2.5 py-1 transition-colors",
              active
                ? isLight
                  ? "bg-white text-[#003087]"
                  : "bg-primary text-primary-foreground"
                : isLight
                  ? "text-white hover:bg-white/10"
                  : "text-muted-foreground hover:bg-muted"
            )}
          >
            {l.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}
