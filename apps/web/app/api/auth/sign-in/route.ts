import { NextResponse } from "next/server";
import { createSession, sessionCookie, validCredentials } from "@/lib/session";
export async function POST(request: Request) {
  const form = await request.formData();
  const user = String(form.get("username") ?? "");
  const password = String(form.get("password") ?? "");
  if (!validCredentials(user, password))
    return NextResponse.redirect(
      new URL("/sign-in?error=credentials", request.url),
      303,
    );
  const response = NextResponse.redirect(new URL("/pages", request.url), 303);
  response.cookies.set(sessionCookie, createSession(user), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 28800,
  });
  return response;
}
