"use client";

import Link from "next/link";
import { Home, MoveLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-gray-50 px-4 text-center">
      <div className="space-y-2">
        <p className="text-8xl font-bold text-primary/20">404</p>
        <h1 className="text-2xl font-semibold text-gray-900">Không tìm thấy trang</h1>
        <p className="text-sm text-gray-500">
          Trang bạn đang tìm không tồn tại hoặc đã bị di chuyển.
        </p>
      </div>
      <div className="flex gap-3">
        <Button variant="outline" onClick={() => window.history.back()}>
          <MoveLeft className="mr-2 h-4 w-4" />
          Quay lại
        </Button>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 py-2 transition-colors"
        >
          <Home className="mr-2 h-4 w-4" />
          Trang chủ
        </Link>
      </div>
    </div>
  );
}
