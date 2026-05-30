import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, Lock, Mail } from "lucide-react";

import { loginUser } from "../../api/authApi";
import Spinner from "../../components/common/Spinner";

function Login() {
  const [email, setEmail] = useState("sandeep@test.com");
  const [password, setPassword] = useState("123456");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const navigate = useNavigate();

  async function handleLogin(event) {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const response = await loginUser({
        email,
        password
      });

      localStorage.setItem(
        "open_analytics_token",
        response.data.access_token
      );

      localStorage.setItem(
        "open_analytics_user",
        JSON.stringify(response.data)
      );

      navigate("/dashboard");
    } catch (error) {
      setMessage(
        error.response?.data?.detail || "Login failed. Please check details."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="oa-app-font flex min-h-screen items-center justify-center bg-oa-dark px-3 text-oa-text">
      <div className="w-full max-w-sm rounded-xl border border-oa-border bg-oa-card p-5 shadow-2xl">
        <div className="mb-5 flex items-center justify-center gap-1">
          <ChevronRight
            size={24}
            strokeWidth={2.6}
            className="text-oa-text"
          />

          <h1 className="text-xl font-semibold tracking-wide">
            Open Analytics
          </h1>
        </div>

        <form onSubmit={handleLogin} className="space-y-3">
          <div>
            <label className="mb-1.5 block text-xs text-oa-muted">
              Email
            </label>

            <div className="flex items-center gap-2 rounded-lg border border-oa-border bg-black px-3 py-2.5 focus-within:border-oa-accent">
              <Mail size={16} className="text-oa-muted" />

              <input
                type="email"
                className="w-full bg-transparent text-sm outline-none"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
              />
            </div>
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="block text-xs text-oa-muted">
                Password
              </label>

              <button
                type="button"
                className="text-xs text-oa-muted transition hover:text-white"
              >
                Forgotten password?
              </button>
            </div>

            <div className="flex items-center gap-2 rounded-lg border border-oa-border bg-black px-3 py-2.5 focus-within:border-oa-accent">
              <Lock size={16} className="text-oa-muted" />

              <input
                type="password"
                className="w-full bg-transparent text-sm outline-none"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Password"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex h-10 w-full items-center justify-center rounded-lg bg-white text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <Spinner size="sm" color="dark" />
                Logging in
              </span>
            ) : (
              "Login"
            )}
          </button>
        </form>

        {message && (
          <div className="mt-3 rounded-lg border border-oa-border bg-black px-3 py-2 text-xs text-oa-muted">
            {message}
          </div>
        )}
      </div>
    </div>
  );
}

export default Login;