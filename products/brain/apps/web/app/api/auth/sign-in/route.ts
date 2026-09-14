import { NextResponse } from "next/server";
import { createSession, sessionCookie, validCredentials } from "@/lib/session";

function requestOrigin(request: Request) {
  const url = new URL(request.url);
  const protocol =
    request.headers.get("x-forwarded-proto")?.split(",", 1)[0]?.trim() ||
    url.protocol.slice(0, -1);
  const host =
    request.headers.get("x-forwarded-host")?.split(",", 1)[0]?.trim() ||
    request.headers.get("host") ||
    url.host;
  return `${protocol}://${host}`;
}

export async function POST(request: Request) {
  const form = await request.formData();
  const user = String(form.get("username") ?? "");
  const password = String(form.get("password") ?? "");
  const origin = requestOrigin(request);
  if (!validCredentials(user, password))
    return NextResponse.redirect(
      new URL("/sign-in?error=credentials", origin),
      303,
    );
  const response = NextResponse.redirect(new URL("/pages", origin), 303);
  const forwardedProtocol = request.headers
    .get("x-forwarded-proto")
    ?.split(",", 1)[0]
    ?.trim();
  response.cookies.set(sessionCookie, createSession(user), {
    httpOnly: true,
    sameSite: "lax",
    secure: forwardedProtocol === "https" || origin.startsWith("https://"),
    path: "/",
    maxAge: 28800,
  });
  return response;
}
