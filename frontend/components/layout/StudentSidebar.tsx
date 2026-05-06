"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/auth";
import { useT, type TKey } from "@/lib/i18n";
import LanguageToggle from "@/components/LanguageToggle";
import NotificationBell from "@/components/layout/NotificationBell";

const NAV_ITEMS: { href: string; labelKey: TKey; icon: string }[] = [
  { href: "/student/dashboard",   labelKey: "nav.dashboard",   icon: "📊" },
  { href: "/student/grades",      labelKey: "nav.grades",      icon: "📝" },
  { href: "/student/warnings",    labelKey: "nav.warnings",    icon: "⚠️" },
  { href: "/student/predictions", labelKey: "nav.predictions", icon: "🤖" },
  { href: "/student/study-plan",  labelKey: "nav.studyPlan",   icon: "🎯" },
  { href: "/student/chatbot",     labelKey: "nav.chatbot",     icon: "💬" },
  { href: "/student/events",      labelKey: "nav.events",      icon: "📅" },
  { href: "/student/notifications", labelKey: "nav.notifications", icon: "🔔" },
];

export default function StudentSidebar() {
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
      {/* Logo */}
      <div className="px-6 py-5 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-white/20 rounded-lg flex items-center justify-center font-bold text-sm">
            BK
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-sm leading-tight">{t("nav.title")}</p>
            <p className="text-xs text-white/60">{t("nav.subtitle")}</p>
          </div>
          <NotificationBell />
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
              pathname === item.href
                ? "bg-white/20 font-medium"
                : "hover:bg-white/10 text-white/80"
            )}
          >
            <span>{item.icon}</span>
            {t(item.labelKey)}
          </Link>
        ))}
      </nav>

      {/* Language toggle + User info + logout */}
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
