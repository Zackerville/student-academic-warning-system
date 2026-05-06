"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const content = {
  vi: {
    title: "Hệ thống AI Cảnh báo Học tập",
    university: "Trường Đại học Bách Khoa TP.HCM",
    description:
      "Hệ thống thông minh hỗ trợ phát hiện sớm nguy cơ học vụ, tư vấn cá nhân hoá và cải thiện kết quả học tập cho sinh viên.",
    login: "Đăng nhập",
    features: [
      { icon: "🤖", label: "Dự đoán AI" },
      { icon: "⚠️", label: "Cảnh báo sớm" },
      { icon: "💬", label: "Tư vấn quy chế" },
    ],
  },
  en: {
    title: "AI Academic Warning System",
    university: "Ho Chi Minh City University of Technology",
    description:
      "An intelligent system for early detection of academic risks, personalised counseling and improving student learning outcomes.",
    login: "Login",
    features: [
      { icon: "🤖", label: "AI Prediction" },
      { icon: "⚠️", label: "Early Warning" },
      { icon: "💬", label: "Regulation Advisor" },
    ],
  },
};

export default function HomePage() {
  const [lang, setLang] = useState<"vi" | "en">("vi");
  const t = content[lang];

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Navbar ─────────────────────────────────────────── */}
      <nav className="bg-[#003087] text-white px-6 py-3 flex items-center justify-between sticky top-0 z-50 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-white rounded-full flex items-center justify-center shadow">
            <span className="text-[#003087] font-bold text-sm">BK</span>
          </div>
          <span className="font-semibold text-sm hidden sm:block tracking-wide">
            HCMUT
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Language toggle */}
          <div className="flex items-center rounded-md overflow-hidden border border-white/30 text-sm">
            <button
              onClick={() => setLang("vi")}
              className={`px-3 py-1.5 transition-colors font-medium ${
                lang === "vi"
                  ? "bg-white text-[#003087]"
                  : "text-white hover:bg-white/10"
              }`}
            >
              VI
            </button>
            <button
              onClick={() => setLang("en")}
              className={`px-3 py-1.5 transition-colors font-medium ${
                lang === "en"
                  ? "bg-white text-[#003087]"
                  : "text-white hover:bg-white/10"
              }`}
            >
              EN
            </button>
          </div>

          <Link href="/auth/login">
            <Button
              variant="outline"
              className="border-white text-white hover:bg-white hover:text-[#003087] bg-transparent text-sm font-semibold"
            >
              {t.login}
            </Button>
          </Link>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────────── */}
      <div className="relative flex-1 flex items-center justify-center overflow-hidden bg-[#003087]">
        {/* Background gradient layers */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#003087] via-[#004ab3] to-[#001a52]" />

        {/* Subtle grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />

        {/* Decorative circles */}
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-white/5 blur-3xl" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-blue-400/10 blur-3xl" />
        <div className="absolute top-1/2 left-1/4 w-64 h-64 rounded-full bg-blue-300/5 blur-2xl" />

        {/* Center content */}
        <div className="relative text-center text-white px-6 py-24 max-w-2xl mx-auto">
          {/* BK logo */}
          <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center mx-auto mb-8 shadow-2xl ring-4 ring-white/20">
            <span className="text-[#003087] font-bold text-3xl">BK</span>
          </div>

          {/* University name */}
          <p className="text-blue-300 text-sm font-medium tracking-widest uppercase mb-4">
            {t.university}
          </p>

          {/* Main title */}
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight mb-6 drop-shadow-lg">
            {t.title}
          </h1>

          {/* Description */}
          <p className="text-blue-100/80 text-base md:text-lg mb-10 max-w-xl mx-auto leading-relaxed">
            {t.description}
          </p>

          {/* Feature pills */}
          <div className="flex items-center justify-center gap-3 mb-10 flex-wrap">
            {t.features.map((f) => (
              <span
                key={f.label}
                className="flex items-center gap-1.5 bg-white/10 border border-white/20 rounded-full px-4 py-1.5 text-sm text-white/90"
              >
                {f.icon} {f.label}
              </span>
            ))}
          </div>

        </div>
      </div>
    </div>
  );
}
