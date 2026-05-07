"use client";

import { useEffect, useState } from "react";
import { X, ArrowRight, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

const TOUR_KEY = "student_tour_done";

const STEPS = [
  {
    title: "Chào mừng đến với Hệ thống Cảnh báo Học vụ AI! 🎓",
    description:
      "Hệ thống giúp bạn theo dõi tình hình học tập, nhận cảnh báo sớm và được tư vấn quy chế trực tiếp. Hãy để chúng tôi hướng dẫn nhanh cho bạn!",
    hint: null,
  },
  {
    title: "Dashboard cá nhân 📊",
    description:
      "Xem GPA tích lũy, số tín chỉ, mức cảnh báo và xu hướng GPA theo từng học kỳ ngay tại trang chủ.",
    hint: "Trang: Dashboard",
  },
  {
    title: "Import bảng điểm từ myBK 📥",
    description:
      "Vào trang Bảng điểm, copy toàn bộ bảng điểm từ cổng myBK và paste vào — hệ thống tự nhận diện và cập nhật GPA cho bạn.",
    hint: "Trang: Bảng điểm",
  },
  {
    title: "AI Risk Score 🔮",
    description:
      "Hệ thống AI phân tích dữ liệu học tập và cho bạn biết nguy cơ bị cảnh báo học vụ (0–100%) cùng các lý do cụ thể. Bạn còn có thể mô phỏng điểm giả định!",
    hint: "Trang: Dự đoán AI",
  },
  {
    title: "Chatbot tư vấn quy chế 💬",
    description:
      "Có thắc mắc về quy chế đào tạo? Chatbot AI sẵn sàng giải đáp 24/7 với trích dẫn từ tài liệu chính thức của trường.",
    hint: "Trang: Chatbot",
  },
];

export default function OnboardingTour() {
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && !localStorage.getItem(TOUR_KEY)) {
      setVisible(true);
    }
  }, []);

  const dismiss = () => {
    localStorage.setItem(TOUR_KEY, "1");
    setVisible(false);
  };

  const next = () => {
    if (step < STEPS.length - 1) {
      setStep((s) => s + 1);
    } else {
      dismiss();
    }
  };

  if (!visible) return null;

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-md mx-4 p-6 relative">
        {/* Close */}
        <button
          onClick={dismiss}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
          aria-label="Đóng"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Progress dots */}
        <div className="flex gap-1.5 mb-5">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all ${
                i === step
                  ? "w-6 bg-primary"
                  : i < step
                  ? "w-3 bg-primary/50"
                  : "w-3 bg-muted"
              }`}
            />
          ))}
        </div>

        {/* Content */}
        <h2 className="text-lg font-bold leading-snug mb-2">{current.title}</h2>
        <p className="text-sm text-muted-foreground leading-relaxed mb-4">
          {current.description}
        </p>
        {current.hint && (
          <p className="text-xs text-primary font-medium mb-4">→ {current.hint}</p>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between mt-2">
          <button
            onClick={dismiss}
            className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-2"
          >
            Bỏ qua hướng dẫn
          </button>
          <Button size="sm" onClick={next}>
            {isLast ? (
              <>
                <CheckCircle className="h-4 w-4 mr-1" />
                Bắt đầu
              </>
            ) : (
              <>
                Tiếp
                <ArrowRight className="h-4 w-4 ml-1" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
