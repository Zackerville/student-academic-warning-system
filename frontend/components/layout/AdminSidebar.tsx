"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/auth";
import { useT, type TKey } from "@/lib/i18n";
import LanguageToggle from "@/components/LanguageToggle";

const NAV_ITEMS: { href: string; labelKey: TKey; icon: string }[] = [
  { href: "/admin/dashboard",  labelKey: "adminNav.dashboard",  icon: "📈" },
  { href: "/admin/students",   labelKey: "adminNav.students",   icon: "👥" },
  { href: "/admin/warnings",   labelKey: "adminNav.warnings",   icon: "🚨" },
  { href: "/admin/import",     labelKey: "adminNav.import",     icon: "📥" },
  { href: "/admin/documents",  labelKey: "adminNav.documents",  icon: "📄" },
  { href: "/admin/events",     labelKey: "adminNav.events",     icon: "📅" },
  { href: "/admin/reports",    labelKey: "adminNav.reports",    icon: "📊" },
];

export default function AdminSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();
  const t = useT();

  const handleLogout = () => {
    clearAuth();
    router.push("/auth/login");
  };

  return (
    <aside className="sticky top-0 flex flex-col w-64 h-screen bg-primary text-white shrink-0">
      <div className="px-6 py-5 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-white/20 rounded-lg flex items-center justify-center font-bold text-sm">
            BK
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-sm leading-tight">{t("adminNav.title")}</p>
            <p className="text-xs text-white/60">{t("adminNav.subtitle")}</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
              pathname === item.href || pathname.startsWith(item.href + "/")
                ? "bg-white/20 font-medium"
                : "hover:bg-white/10 text-white/80"
            )}
          >
            <span>{item.icon}</span>
            {t(item.labelKey)}
          </Link>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-white/10 space-y-3 shrink-0">
        <LanguageToggle variant="light" />
        <p className="text-xs text-white/60 truncate">{user?.email}</p>
        <button
          onClick={handleLogout}
          className="text-sm text-white/80 hover:text-white transition-colors"
        >
          {t("nav.logout")}
        </button>
      </div>
    </aside>
  );
}
