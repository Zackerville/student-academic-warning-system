"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/api";

const FACULTIES = [
  "Khoa CNTT",
  "Khoa Điện – Điện tử",
  "Khoa Cơ khí",
  "Khoa Xây dựng",
  "Khoa Hóa",
  "Khoa Kinh tế",
];

const registerSchema = z.object({
  email: z.string().email("Email không hợp lệ"),
  password: z.string().min(8, "Mật khẩu tối thiểu 8 ký tự"),
  mssv: z.string().min(7, "MSSV không hợp lệ").max(20),
  full_name: z.string().min(2, "Họ tên quá ngắn").max(255),
  faculty: z.string().min(1, "Chọn khoa"),
  major: z.string().min(2, "Ngành học quá ngắn").max(255),
  cohort: z
    .string()
    .refine((v) => /^\d{4}$/.test(v) && +v >= 2000 && +v <= 2030, {
      message: "Khóa phải từ 2000 đến 2030",
    }),
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (data: RegisterForm) => {
    setError(null);
    try {
      await authApi.register({ ...data, cohort: Number(data.cohort) });
      setSuccess(true);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Đăng ký thất bại. Vui lòng thử lại.");
    }
  };

  return (
    <Card className="w-full max-w-lg shadow-2xl">
      <CardHeader className="space-y-1 text-center">
        <div className="flex justify-center mb-2">
          <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center text-white font-bold text-lg">
            BK
          </div>
        </div>
        <CardTitle className="text-2xl font-bold text-primary">Đăng ký tài khoản</CardTitle>
        <CardDescription>Hệ thống Cảnh báo Học vụ – HCMUT</CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {success && (
            <div className="rounded-md bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3 text-center space-y-2">
              <p className="font-medium">Đăng ký thành công!</p>
              <Link href="/login" className="inline-block text-primary font-medium hover:underline">
                Về trang đăng nhập →
              </Link>
            </div>
          )}
          {error && (
            <div className="rounded-md bg-destructive/10 text-destructive text-sm px-3 py-2">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="mssv">MSSV</Label>
              <Input id="mssv" placeholder="2110001" {...register("mssv")} />
              {errors.mssv && <p className="text-xs text-destructive">{errors.mssv.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="cohort">Khóa</Label>
              <Input id="cohort" type="number" placeholder="2021" {...register("cohort")} />
              {errors.cohort && <p className="text-xs text-destructive">{errors.cohort.message}</p>}
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="full_name">Họ và tên</Label>
            <Input id="full_name" placeholder="Nguyễn Văn A" {...register("full_name")} />
            {errors.full_name && <p className="text-xs text-destructive">{errors.full_name.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="faculty">Khoa</Label>
              <select
                id="faculty"
                {...register("faculty")}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="">Chọn khoa</option>
                {FACULTIES.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
              {errors.faculty && <p className="text-xs text-destructive">{errors.faculty.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="major">Ngành học</Label>
              <Input id="major" placeholder="Khoa học Máy tính" {...register("major")} />
              {errors.major && <p className="text-xs text-destructive">{errors.major.message}</p>}
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" placeholder="email@hcmut.edu.vn" {...register("email")} />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>

          <div className="space-y-1">
            <Label htmlFor="password">Mật khẩu</Label>
            <Input id="password" type="password" placeholder="Tối thiểu 8 ký tự" {...register("password")} />
            {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
          </div>
        </CardContent>

        <CardFooter className="flex flex-col gap-3">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Đang đăng ký..." : "Đăng ký"}
          </Button>
          <p className="text-sm text-muted-foreground text-center">
            Đã có tài khoản?{" "}
            <Link href="/login" className="text-primary font-medium hover:underline">
              Đăng nhập
            </Link>
          </p>
          <Link href="/" className="text-xs text-muted-foreground hover:text-primary transition-colors">
            ← Về trang chủ
          </Link>
        </CardFooter>
      </form>
    </Card>
  );
}