import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_EXACT = ["/"];
const PUBLIC_PREFIX = ["/auth/login", "/auth/admin-login", "/auth/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_EXACT.includes(pathname)) return NextResponse.next();
  if (PUBLIC_PREFIX.some((p) => pathname.startsWith(p))) return NextResponse.next();

  // Check for token in cookie (set by auth store hydration)
  const token = request.cookies.get("access_token")?.value;
  if (!token) {
    const url = request.nextUrl.clone();
    url.pathname = "/auth/login";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
