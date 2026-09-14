import { NextResponse } from "next/server";
import { sessionCookie } from "@/lib/session";
export async function POST(request: Request) {
  const response = NextResponse.redirect(new URL("/sign-in", request.url), 303);
  response.cookies.set(sessionCookie, "", {
    httpOnly: true,
    path: "/",
    maxAge: 0,
  });
  return response;
}
