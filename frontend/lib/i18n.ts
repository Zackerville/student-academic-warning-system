"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Lang = "vi" | "en";

interface I18nState {
  lang: Lang;
  setLang: (l: Lang) => void;
}

export const useI18nStore = create<I18nState>()(
  persist(
    (set) => ({
      lang: "vi",
      setLang: (lang) => set({ lang }),
    }),
    { name: "lang-storage" }
  )
);

// ─── Translation dictionary ──────────────────────────────────
// Add new keys here when needed. Both `vi` and `en` must have the same keys.

const dict = {
  vi: {
    // Navbar / Sidebar
    "nav.title": "Cảnh báo Học vụ",
    "nav.subtitle": "HCMUT",
    "nav.dashboard": "Tổng quan",
    "nav.grades": "Điểm số",
    "nav.warnings": "Cảnh báo",
    "nav.predictions": "Dự báo AI",
    "nav.chatbot": "Tư vấn AI",
    "nav.events": "Sự kiện",
    "nav.logout": "Đăng xuất",

    // Common
    "common.loading": "Đang tải...",
    "common.save": "Lưu",
    "common.saving": "Đang lưu...",
    "common.cancel": "Hủy",
    "common.delete": "Xóa",
    "common.confirm": "Xác nhận",
    "common.back": "Quay lại",
    "common.unknownError": "Lỗi không xác định",

    // Login
    "login.title": "Đăng nhập",
    "login.subtitle": "Hệ thống Cảnh báo Học vụ – HCMUT",
    "login.email": "Email",
    "login.password": "Mật khẩu",
    "login.submit": "Đăng nhập",
    "login.submitting": "Đang đăng nhập...",
    "login.noAccount": "Chưa có tài khoản?",
    "login.signupLink": "Đăng ký",
    "login.backHome": "← Về trang chủ",
    "login.error": "Đăng nhập thất bại. Vui lòng kiểm tra lại.",
    "login.invalidEmail": "Email không hợp lệ",
    "login.passwordRequired": "Mật khẩu không được để trống",

    // Register
    "register.title": "Đăng ký tài khoản",
    "register.subtitle": "Hệ thống Cảnh báo Học vụ – HCMUT",
    "register.mssv": "MSSV",
    "register.cohort": "Khóa",
    "register.fullName": "Họ và tên",
    "register.faculty": "Khoa",
    "register.facultyPlaceholder": "Chọn khoa",
    "register.major": "Ngành học",
    "register.email": "Email",
    "register.password": "Mật khẩu",
    "register.passwordHint": "Tối thiểu 8 ký tự",
    "register.submit": "Đăng ký",
    "register.submitting": "Đang đăng ký...",
    "register.haveAccount": "Đã có tài khoản?",
    "register.loginLink": "Đăng nhập",
    "register.success": "Đăng ký thành công!",
    "register.successCta": "Về trang đăng nhập →",
    "register.error": "Đăng ký thất bại. Vui lòng thử lại.",
    "register.invalidMssv": "MSSV không hợp lệ",
    "register.shortName": "Họ tên quá ngắn",
    "register.shortMajor": "Ngành học quá ngắn",
    "register.shortPassword": "Mật khẩu tối thiểu 8 ký tự",
    "register.invalidEmail": "Email không hợp lệ",
    "register.facultyRequired": "Chọn khoa",
    "register.invalidCohort": "Khóa phải từ 2000 đến 2030",

    // Dashboard
    "dashboard.title": "Tổng quan",
    "dashboard.greeting": "Xin chào,",
    "dashboard.warning.0": "Bình thường",
    "dashboard.warning.1": "Cảnh báo mức 1",
    "dashboard.warning.2": "Cảnh báo mức 2",
    "dashboard.warning.3": "Buộc thôi học",
    "dashboard.gpaCumulative": "GPA Tích lũy",
    "dashboard.gpaScale": "Thang điểm 4",
    "dashboard.creditsEarned": "Tín chỉ tích lũy",
    "dashboard.currentSemester": "HK hiện tại:",
    "dashboard.creditsInProgress": "TC đang học",
    "dashboard.thisSemester": "Học kỳ này",
    "dashboard.failedTotal": "Môn rớt (tổng)",
    "dashboard.gpaTrend": "Xu hướng GPA theo học kỳ",
    "dashboard.semesterDetails": "Chi tiết từng học kỳ",
    "dashboard.tableSemester": "Học kỳ",
    "dashboard.tableGpa": "GPA HK",
    "dashboard.tableCredits": "TC đã học",
    "dashboard.tableCourses": "Số môn",
    "dashboard.empty.title": "Chưa có dữ liệu điểm.",
    "dashboard.empty.cta": "Vào trang Bảng điểm để nhập điểm từ myBK hoặc tự nhập thủ công.",
    "dashboard.loadError": "Không thể tải dữ liệu. Vui lòng thử lại.",

    // Grades
    "grades.title": "Bảng điểm",
    "grades.subtitle": "Quản lý điểm các môn học",
    "grades.addCourse": "Thêm môn học",
    "grades.importMyBK": "Cập nhật từ myBK",
    "grades.filter": "Lọc:",
    "grades.filterAll": "Tất cả",
    "grades.semester": "HK",
    "grades.empty": "Chưa có dữ liệu điểm.",
    "grades.status.enrolled": "Đang học",
    "grades.status.passed": "Đạt",
    "grades.status.failed": "Không đạt",
    "grades.status.withdrawn": "Rút môn",
    "grades.status.exempt": "Miễn",
    "grades.credits": "tín chỉ",
    "grades.enterScore": "Nhập điểm",
    "grades.scoreMidterm": "GK",
    "grades.scoreLab": "TN",
    "grades.scoreOther": "BTL",
    "grades.scoreFinal": "CK",
    "grades.attendance": "Điểm danh %",
    "grades.attendanceLabel": "Điểm danh:",
    "grades.delete": "Xoá",
    "grades.deleteAll": "Xoá tất cả",
    "grades.deleteConfirm": "Bạn có chắc muốn xoá môn này?",
    "grades.deleteAllTitle": "Xoá toàn bộ bảng điểm?",
    "grades.deleteAllWarning": "Hành động này sẽ xoá vĩnh viễn TẤT CẢ môn học của bạn (cả môn nhập tay lẫn môn import từ myBK). GPA sẽ về 0. Hành động này không thể hoàn tác.",
    "grades.deleteAllConfirm": "Tôi hiểu, xoá tất cả",
    "grades.deleteAllSuccess": "Đã xoá {n} môn học",
    "grades.deleting": "Đang xoá...",

    // myBK Import
    "mybk.title": "Cập nhật từ myBK",
    "mybk.description": "Dán nội dung bảng điểm copy từ trang myBK để tự động cập nhật tất cả môn học.",
    "mybk.guideTitle": "Hướng dẫn:",
    "mybk.guide1": "Mở myBK → Kết quả học tập → Bảng điểm học kỳ",
    "mybk.guide2": "Nhấn",
    "mybk.guide2b": "rồi",
    "mybk.guide3": "Dán vào ô bên dưới và nhấn Import",
    "mybk.pasteLabel": "Dán nội dung từ myBK",
    "mybk.import": "Import từ myBK",
    "mybk.importing": "Đang import...",
    "mybk.success": "Học kỳ:",
    "mybk.created": "Tạo mới:",
    "mybk.updated": "Cập nhật:",
    "mybk.totalCourses": "Tổng:",
    "mybk.coursesUnit": "môn",
    "mybk.error": "Import thất bại. Vui lòng thử lại.",

    // Add Course Dialog
    "addCourse.title": "Thêm môn học",
    "addCourse.code": "Mã môn *",
    "addCourse.name": "Tên môn *",
    "addCourse.semester": "Học kỳ * (VD: 241)",
    "addCourse.credits": "Số tín chỉ",
    "addCourse.weightStructure": "Cấu trúc điểm",
    "addCourse.scoresLabel": "Điểm thành phần (để trống nếu chưa có)",
    "addCourse.scoreMidterm": "Giữa kỳ — GK",
    "addCourse.scoreLab": "Thí nghiệm — TN",
    "addCourse.scoreOther": "BTL / Đồ án",
    "addCourse.scoreFinal": "Cuối kỳ — CK",
    "addCourse.attendance": "Tỉ lệ điểm danh (%)",
    "addCourse.submit": "Thêm môn",
    "addCourse.weightSumOk": "Tổng = 100% ✓",
    "addCourse.weightSumError": "Tổng phải = 100% (hiện:",
    "addCourse.fillRequired": "Vui lòng điền đầy đủ mã môn, tên môn và học kỳ.",
    "addCourse.failed": "Thêm môn thất bại.",
  },
  en: {
    // Navbar / Sidebar
    "nav.title": "Academic Warning",
    "nav.subtitle": "HCMUT",
    "nav.dashboard": "Dashboard",
    "nav.grades": "Grades",
    "nav.warnings": "Warnings",
    "nav.predictions": "AI Predictions",
    "nav.chatbot": "AI Advisor",
    "nav.events": "Events",
    "nav.logout": "Logout",

    // Common
    "common.loading": "Loading...",
    "common.save": "Save",
    "common.saving": "Saving...",
    "common.cancel": "Cancel",
    "common.delete": "Delete",
    "common.confirm": "Confirm",
    "common.back": "Back",
    "common.unknownError": "Unknown error",

    // Login
    "login.title": "Login",
    "login.subtitle": "Academic Warning System – HCMUT",
    "login.email": "Email",
    "login.password": "Password",
    "login.submit": "Login",
    "login.submitting": "Logging in...",
    "login.noAccount": "No account yet?",
    "login.signupLink": "Sign up",
    "login.backHome": "← Back to home",
    "login.error": "Login failed. Please check your credentials.",
    "login.invalidEmail": "Invalid email",
    "login.passwordRequired": "Password is required",

    // Register
    "register.title": "Create Account",
    "register.subtitle": "Academic Warning System – HCMUT",
    "register.mssv": "Student ID",
    "register.cohort": "Cohort",
    "register.fullName": "Full Name",
    "register.faculty": "Faculty",
    "register.facultyPlaceholder": "Select faculty",
    "register.major": "Major",
    "register.email": "Email",
    "register.password": "Password",
    "register.passwordHint": "At least 8 characters",
    "register.submit": "Sign Up",
    "register.submitting": "Signing up...",
    "register.haveAccount": "Already have an account?",
    "register.loginLink": "Login",
    "register.success": "Registration successful!",
    "register.successCta": "Go to login →",
    "register.error": "Registration failed. Please try again.",
    "register.invalidMssv": "Invalid student ID",
    "register.shortName": "Name is too short",
    "register.shortMajor": "Major name is too short",
    "register.shortPassword": "Password must be at least 8 characters",
    "register.invalidEmail": "Invalid email",
    "register.facultyRequired": "Please select a faculty",
    "register.invalidCohort": "Cohort must be between 2000 and 2030",

    // Dashboard
    "dashboard.title": "Dashboard",
    "dashboard.greeting": "Hello,",
    "dashboard.warning.0": "Normal",
    "dashboard.warning.1": "Warning Level 1",
    "dashboard.warning.2": "Warning Level 2",
    "dashboard.warning.3": "Forced Withdrawal",
    "dashboard.gpaCumulative": "Cumulative GPA",
    "dashboard.gpaScale": "4.0 scale",
    "dashboard.creditsEarned": "Credits Earned",
    "dashboard.currentSemester": "Current sem:",
    "dashboard.creditsInProgress": "Credits in Progress",
    "dashboard.thisSemester": "This semester",
    "dashboard.failedTotal": "Failed Courses (total)",
    "dashboard.gpaTrend": "GPA Trend by Semester",
    "dashboard.semesterDetails": "Semester Details",
    "dashboard.tableSemester": "Semester",
    "dashboard.tableGpa": "Sem GPA",
    "dashboard.tableCredits": "Credits Taken",
    "dashboard.tableCourses": "Courses",
    "dashboard.empty.title": "No grade data yet.",
    "dashboard.empty.cta": "Go to the Grades page to import from myBK or enter scores manually.",
    "dashboard.loadError": "Failed to load data. Please try again.",

    // Grades
    "grades.title": "Grades",
    "grades.subtitle": "Manage course scores",
    "grades.addCourse": "Add Course",
    "grades.importMyBK": "Import from myBK",
    "grades.filter": "Filter:",
    "grades.filterAll": "All",
    "grades.semester": "Sem",
    "grades.empty": "No grade data yet.",
    "grades.status.enrolled": "Enrolled",
    "grades.status.passed": "Passed",
    "grades.status.failed": "Failed",
    "grades.status.withdrawn": "Withdrawn",
    "grades.status.exempt": "Exempt",
    "grades.credits": "credits",
    "grades.enterScore": "Enter scores",
    "grades.scoreMidterm": "Mid",
    "grades.scoreLab": "Lab",
    "grades.scoreOther": "Proj",
    "grades.scoreFinal": "Final",
    "grades.attendance": "Attendance %",
    "grades.attendanceLabel": "Attendance:",
    "grades.delete": "Delete",
    "grades.deleteAll": "Delete all",
    "grades.deleteConfirm": "Are you sure you want to delete this course?",
    "grades.deleteAllTitle": "Delete all grades?",
    "grades.deleteAllWarning": "This will permanently delete ALL your courses (both manually entered and myBK-imported). GPA will reset to 0. This action cannot be undone.",
    "grades.deleteAllConfirm": "I understand, delete all",
    "grades.deleteAllSuccess": "Deleted {n} courses",
    "grades.deleting": "Deleting...",

    // myBK Import
    "mybk.title": "Import from myBK",
    "mybk.description": "Paste the transcript copied from myBK to auto-update all courses.",
    "mybk.guideTitle": "Instructions:",
    "mybk.guide1": "Open myBK → Academic Result → Semester Transcript",
    "mybk.guide2": "Press",
    "mybk.guide2b": "then",
    "mybk.guide3": "Paste below and click Import",
    "mybk.pasteLabel": "Paste content from myBK",
    "mybk.import": "Import from myBK",
    "mybk.importing": "Importing...",
    "mybk.success": "Semesters:",
    "mybk.created": "Created:",
    "mybk.updated": "Updated:",
    "mybk.totalCourses": "Total:",
    "mybk.coursesUnit": "courses",
    "mybk.error": "Import failed. Please try again.",

    // Add Course Dialog
    "addCourse.title": "Add Course",
    "addCourse.code": "Course Code *",
    "addCourse.name": "Course Name *",
    "addCourse.semester": "Semester * (e.g., 241)",
    "addCourse.credits": "Credits",
    "addCourse.weightStructure": "Score Structure",
    "addCourse.scoresLabel": "Component scores (leave blank if not yet)",
    "addCourse.scoreMidterm": "Midterm — Mid",
    "addCourse.scoreLab": "Lab",
    "addCourse.scoreOther": "Project",
    "addCourse.scoreFinal": "Final",
    "addCourse.attendance": "Attendance rate (%)",
    "addCourse.submit": "Add Course",
    "addCourse.weightSumOk": "Total = 100% ✓",
    "addCourse.weightSumError": "Total must = 100% (current:",
    "addCourse.fillRequired": "Please fill in course code, name and semester.",
    "addCourse.failed": "Failed to add course.",
  },
} as const;

export type TKey = keyof (typeof dict)["vi"];

/**
 * React hook returning a translator function `t(key)`.
 * Component re-renders when language changes.
 */
export function useT() {
  const lang = useI18nStore((s) => s.lang);
  return (key: TKey): string => {
    const table = dict[lang] as Record<string, string>;
    return table[key] ?? key;
  };
}
