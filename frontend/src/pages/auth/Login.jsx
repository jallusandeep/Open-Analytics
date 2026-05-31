import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, Lock, UserRound } from "lucide-react";

import { loginUser } from "../../api/authApi";
import FloatingInput from "../../components/common/FloatingInput";
import Spinner from "../../components/common/Spinner";

function Login() {
  const [loginIdentifier, setLoginIdentifier] = useState("sandeep@test.com");
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
        login_identifier: loginIdentifier,
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
        <div className="mb-6 flex items-center justify-center gap-1">
          <ChevronRight
            size={24}
            strokeWidth={2.6}
            className="text-oa-text"
          />

          <h1 className="text-xl font-semibold tracking-wide">
            Open Analytics
          </h1>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <FloatingInput
            id="login-identifier"
            name="loginIdentifier"
            label="Login ID / Mobile / Email"
            type="text"
            value={loginIdentifier}
            onChange={(event) => setLoginIdentifier(event.target.value)}
            icon={UserRound}
            autoComplete="username"
            required
            variant="auth"
          />

          <div>
            <FloatingInput
              id="login-password"
              name="password"
              label="Password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              icon={Lock}
              autoComplete="current-password"
              required
              variant="auth"
            />

            <div className="mt-1.5 flex justify-end">
              <button
                type="button"
                className="text-xs text-oa-muted transition hover:text-white"
              >
                Forgotten password?
              </button>
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