"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/auth";

const NAV_ITEMS = [
  { href: "/dashboard",    label: "Tổng quan",       icon: "📊" },
  { href: "/grades",       label: "Điểm số",         icon: "📝" },
  { href: "/warnings",     label: "Cảnh báo",        icon: "⚠️" },
  { href: "/predictions",  label: "Dự báo AI",       icon: "🤖" },
  { href: "/chatbot",      label: "Tư vấn AI",       icon: "💬" },
  { href: "/events",       label: "Sự kiện",         icon: "📅" },
];

export default function StudentSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();

  const handleLogout = () => {
    clearAuth();
    router.push("/login");
  };

  return (
    <aside className="flex flex-col w-64 min-h-screen bg-primary text-white">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-white/20 rounded-lg flex items-center justify-center font-bold text-sm">
            BK
          </div>
          <div>
            <p className="font-semibold text-sm leading-tight">Cảnh báo Học vụ</p>
            <p className="text-xs text-white/60">HCMUT</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
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
            {item.label}
          </Link>
        ))}
      </nav>

      {/* User info + logout */}
      <div className="px-4 py-4 border-t border-white/10">
        <p className="text-xs text-white/60 truncate mb-1">{user?.email}</p>
        <button
          onClick={handleLogout}
          className="text-sm text-white/80 hover:text-white transition-colors"
        >
          Đăng xuất
        </button>
      </div>
    </aside>
  );
}