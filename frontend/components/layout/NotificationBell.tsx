"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bell } from "lucide-react";
import { notificationsApi } from "@/lib/api";

const POLL_MS = 60_000;

export default function NotificationBell() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let alive = true;
    const fetchCount = async () => {
      try {
        const r = await notificationsApi.unreadCount();
        if (alive) setCount(r.data.unread);
      } catch {
        // silent — bell is non-critical
      }
    };
    fetchCount();
    const id = setInterval(fetchCount, POLL_MS);
    return () => { alive = false; clearInterval(id); };
  }, []);

  return (
    <Link
      href="/student/notifications"
      className="relative inline-flex items-center justify-center h-8 w-8 rounded-md hover:bg-white/10 transition-colors"
      aria-label="Notifications"
    >
      <Bell className="h-4 w-4 text-white/90" />
      {count > 0 && (
        <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-[10px] font-semibold text-white flex items-center justify-center">
          {count > 99 ? "99+" : count}
        </span>
      )}
    </Link>
  );
}
