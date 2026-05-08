"use client";

import { useEffect, useState } from "react";
import { Joyride, type EventData, STATUS, type Step } from "react-joyride";

const STORAGE_KEY = "onboarding_tour_done";

const STEPS: Step[] = [
  {
    target: "body",
    content: "Chào mừng đến với Hệ thống Cảnh báo Học vụ HCMUT! Hãy để chúng tôi giới thiệu nhanh các tính năng chính.",
    placement: "center",
    skipBeacon: true,
    title: "👋 Chào mừng!",
  },
  {
    target: "[data-tour='sidebar-dashboard']",
    content: "Tổng quan học tập — GPA tích lũy, tín chỉ, xu hướng GPA theo từng học kỳ.",
    title: "📊 Tổng quan",
    skipBeacon: true,
  },
  {
    target: "[data-tour='sidebar-grades']",
    content: "Nhập điểm thủ công hoặc import bảng điểm từ myBK bằng Ctrl+A copy-paste.",
    title: "📝 Điểm số",
    skipBeacon: true,
  },
  {
    target: "[data-tour='sidebar-predictions']",
    content: "AI phân tích nguy cơ học vụ của bạn dựa trên GPA, môn F, xu hướng điểm. Có cả Mô phỏng what-if.",
    title: "🤖 Dự báo AI",
    skipBeacon: true,
  },
  {
    target: "[data-tour='sidebar-chatbot']",
    content: "Hỏi đáp về quy chế đào tạo và nhận tư vấn cá nhân hóa từ AI.",
    title: "💬 Hỏi đáp & Tư vấn",
    skipBeacon: true,
  },
  {
    target: "[data-tour='sidebar-warnings']",
    content: "Xem lịch sử cảnh báo học vụ và trạng thái xử lý từ phòng đào tạo.",
    title: "⚠️ Cảnh báo",
    skipBeacon: true,
  },
];

export function OnboardingTour() {
  const [run, setRun] = useState(false);

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) {
      const t = setTimeout(() => setRun(true), 800);
      return () => clearTimeout(t);
    }
  }, []);

  const handleEvent = (data: EventData) => {
    const { status } = data;
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      localStorage.setItem(STORAGE_KEY, "1");
      setRun(false);
    }
  };

  if (!run) return null;

  return (
    <Joyride
      steps={STEPS}
      run={run}
      continuous
      scrollToFirstStep
      onEvent={handleEvent}
      options={{
        primaryColor: "hsl(221, 83%, 33%)",
        showProgress: true,
        buttons: ["back", "close", "primary", "skip"],
        zIndex: 10000,
      }}
      locale={{
        back: "Quay lại",
        close: "Đóng",
        last: "Xong!",
        next: "Tiếp theo",
        skip: "Bỏ qua",
        open: "Mở",
      }}
    />
  );
}
