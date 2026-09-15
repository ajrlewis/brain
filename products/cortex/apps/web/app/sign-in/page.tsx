import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { readSession, sessionCookie } from "@/lib/session";
export default async function SignIn({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  if (readSession((await cookies()).get(sessionCookie)?.value)) redirect("/conversations");
  const error = (await searchParams).error;
  return <main className="sign-in"><section className="sign-in-panel"><p className="eyebrow">Mind / Cortex</p><h1>Continue your work.</h1><p className="lede">Sign in to your local Cortex conversation workspace.</p><form action="/api/auth/sign-in" method="post" className="sign-in-form"><label>Username<input name="username" autoComplete="username" required autoFocus /></label><label>Password<input name="password" type="password" autoComplete="current-password" required /></label>{error && <p className="form-error" role="alert">{error === "session" ? "Your Cortex API session is no longer valid." : "The username or password is incorrect."}</p>}<button className="primary" type="submit">Sign in</button></form><small>Local development authentication</small></section></main>;
}
