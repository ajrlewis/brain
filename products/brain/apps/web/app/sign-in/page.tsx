import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { readSession, sessionCookie } from "@/lib/session";
export default async function SignIn({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  if (readSession((await cookies()).get(sessionCookie)?.value))
    redirect("/pages");
  const failed = (await searchParams).error;
  return (
    <main className="sign-in">
      <section className="sign-in-panel">
        <div className="brand sign-in-brand">
          <span className="brand-mark">B</span>
          <span>Brain</span>
        </div>
        <p className="eyebrow">Knowledge console</p>
        <h1>Welcome back.</h1>
        <p className="lede">
          Sign in to browse the governed knowledge available to your identity.
        </p>
        <form action="/api/auth/sign-in" method="post">
          <label>
            Username
            <input name="username" autoComplete="username" required autoFocus />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          {failed && (
            <p className="form-error" role="alert">
              The username or password is incorrect.
            </p>
          )}
          <button className="button" type="submit">
            Sign in
          </button>
        </form>
        <small>Local development authentication</small>
      </section>
      <aside className="sign-in-art">
        <p>One trusted place for</p>
        <strong>
          Pages.
          <br />
          Skills.
          <br />
          Provenance.
        </strong>
      </aside>
    </main>
  );
}
