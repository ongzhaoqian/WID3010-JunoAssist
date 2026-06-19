import { useState } from "react";
import { postJson, setAuthToken } from "../lib/api";

const DEMO_ACCOUNTS = [
  { username: "mackwongyy@gmail.com", password: "12345678" },
  { username: "jonathansiew@hotmail.com", password: "87654321" }
];

export default function AuthPanel({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("mackwongyy@gmail.com");
  const [password, setPassword] = useState("12345678");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await postJson(mode === "signup" ? "/api/auth/signup" : "/api/auth/login", {
        username,
        password
      });
      setAuthToken(result.token);
      onAuthenticated?.(result.user);
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  function useDemoAccount(account) {
    setUsername(account.username);
    setPassword(account.password);
    setMode("login");
  }

  return (
    <main className="relative mx-auto flex min-h-screen max-w-6xl items-center justify-center px-4 py-10 text-white sm:px-6">
      <section className="hero-shell grid w-full overflow-hidden rounded-[2.25rem] p-6 md:grid-cols-[1.05fr_0.95fr] md:p-8">
        <div className="relative z-10 flex flex-col justify-between p-2 md:p-5">
          <div>
            <p className="section-kicker text-sm font-semibold">JUNO Assist</p>
            <h1 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">
              Secure dashboard access
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-7 text-slate-200/85">
              Log in before using schedules, reminders, and fitness records. Each user’s dashboard data is scoped to their own account in the database.
            </p>
          </div>

          <div className="mt-8 rounded-[1.75rem] border border-white/15 bg-white/[0.08] p-4">
            <p className="text-sm font-semibold text-white">Demo accounts</p>
            <div className="mt-3 grid gap-2">
              {DEMO_ACCOUNTS.map((account) => (
                <button
                  key={account.username}
                  type="button"
                  onClick={() => useDemoAccount(account)}
                  className="rounded-2xl border border-white/15 bg-white/[0.08] px-4 py-3 text-left text-sm text-slate-200 transition hover:bg-white/[0.13]"
                >
                  <span className="font-semibold text-white">{account.username}</span>
                  <span className="block text-xs text-slate-300/75">Password: {account.password}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <form onSubmit={submit} className="glass-card relative z-10 rounded-[2rem] p-5 md:p-6">
          <div className="relative z-10">
            <div className="mb-5 flex rounded-2xl border border-white/15 bg-slate-950/30 p-1">
              <button
                type="button"
                onClick={() => setMode("login")}
                className={`flex-1 rounded-xl px-4 py-2 text-sm font-semibold ${mode === "login" ? "btn-primary" : "text-slate-300"}`}
              >
                Log in
              </button>
              <button
                type="button"
                onClick={() => setMode("signup")}
                className={`flex-1 rounded-xl px-4 py-2 text-sm font-semibold ${mode === "signup" ? "btn-primary" : "text-slate-300"}`}
              >
                Sign up
              </button>
            </div>

            <label className="block text-sm font-medium text-slate-200">
              Email username
              <input
                className="input-glass mt-2 w-full rounded-2xl px-4 py-3"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="name@example.com"
                type="email"
                autoComplete="username"
              />
            </label>

            <label className="mt-4 block text-sm font-medium text-slate-200">
              Password
              <input
                className="input-glass mt-2 w-full rounded-2xl px-4 py-3"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Minimum 8 characters"
                type="password"
                autoComplete={mode === "signup" ? "new-password" : "current-password"}
              />
            </label>

            {error && (
              <div className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-400/10 p-3 text-sm text-rose-100">
                {error}
              </div>
            )}

            <button
              disabled={loading}
              className="btn-primary mt-5 w-full px-5 py-3 text-sm font-semibold disabled:opacity-60"
              type="submit"
            >
              {loading ? "Please wait..." : mode === "signup" ? "Create account" : "Log in"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
