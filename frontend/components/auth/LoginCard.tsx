"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, GraduationCap, ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth";
import { useT } from "@/lib/i18n";

type LoginMode = "student" | "admin";

type LoginCardProps = {
  mode: LoginMode;
};

export default function LoginCard({ mode }: LoginCardProps) {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const t = useT();
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const isAdmin = mode === "admin";

  const loginSchema = z.object({
    email: z.string().email(t("login.invalidEmail")),
    password: z.string().min(1, t("login.passwordRequired")),
  });
  type LoginForm = z.infer<typeof loginSchema>;

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (data: LoginForm) => {
    setError(null);
    try {
      const tokenRes = await authApi.login(data);
      const token = tokenRes.data.access_token;
      localStorage.setItem("access_token", token);

      const meRes = await authApi.me();
      if (meRes.data.role !== mode) {
        clearAuth();
        setError(isAdmin ? t("adminLogin.studentAccountError") : t("login.adminAccountError"));
        return;
      }

      setAuth(token, meRes.data);
      router.push(isAdmin ? "/admin/documents" : "/student/dashboard");
    } catch (err: unknown) {
      clearAuth();
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? t("login.error"));
    }
  };

  const Icon = isAdmin ? ShieldCheck : GraduationCap;
  const passwordToggleLabel = showPassword ? t("login.hidePassword") : t("login.showPassword");

  return (
    <Card className="w-full max-w-md shadow-2xl">
      <CardHeader className="space-y-1 text-center">
        <div className="flex justify-center mb-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-white shadow-sm">
            <Icon className="h-6 w-6" />
          </div>
        </div>
        <CardTitle className="text-2xl font-bold text-primary">
          {isAdmin ? t("adminLogin.title") : t("login.title")}
        </CardTitle>
        <CardDescription>
          {isAdmin ? t("adminLogin.subtitle") : t("login.subtitle")}
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {error && (
            <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="space-y-1">
            <Label htmlFor={`${mode}-email`}>{t("login.email")}</Label>
            <Input
              id={`${mode}-email`}
              type="email"
              placeholder={isAdmin ? "admin@hcmut.edu.vn" : "email@hcmut.edu.vn"}
              {...register("email")}
            />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>

          <div className="space-y-1">
            <Label htmlFor={`${mode}-password`}>{t("login.password")}</Label>
            <div className="relative">
              <Input
                id={`${mode}-password`}
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                className="pr-10"
                {...register("password")}
              />
              <button
                type="button"
                aria-label={passwordToggleLabel}
                title={passwordToggleLabel}
                onClick={() => setShowPassword((current) => !current)}
                className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {errors.password && (
              <p className="text-xs text-destructive">{errors.password.message}</p>
            )}
          </div>
        </CardContent>

        <CardFooter className="flex flex-col gap-3">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting
              ? isAdmin
                ? t("adminLogin.submitting")
                : t("login.submitting")
              : isAdmin
                ? t("adminLogin.submit")
                : t("login.submit")}
          </Button>

          {isAdmin ? (
            <p className="text-center text-sm text-muted-foreground">
              {t("adminLogin.studentPrompt")}{" "}
              <Link href="/auth/login" className="font-medium text-primary hover:underline">
                {t("adminLogin.studentLink")}
              </Link>
            </p>
          ) : (
            <>
              <p className="text-center text-sm text-muted-foreground">
                {t("login.noAccount")}{" "}
                <Link href="/auth/register" className="font-medium text-primary hover:underline">
                  {t("login.signupLink")}
                </Link>
              </p>
              <p className="text-center text-sm text-muted-foreground">
                {t("login.adminPrompt")}{" "}
                <Link href="/auth/admin-login" className="font-medium text-primary hover:underline">
                  {t("login.adminLink")}
                </Link>
              </p>
            </>
          )}

          <Link href="/" className="text-xs text-muted-foreground transition-colors hover:text-primary">
            {t("login.backHome")}
          </Link>
        </CardFooter>
      </form>
    </Card>
  );
}
