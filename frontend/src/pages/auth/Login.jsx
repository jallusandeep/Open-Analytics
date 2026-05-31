import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  ChevronRight,
  KeyRound,
  Lock,
  RotateCcw,
  UserRound,
  X
} from "lucide-react";

import {
  loginUser,
  requestForgotPasswordOtp,
  resetPasswordWithOtp
} from "../../api/authApi";
import FloatingInput from "../../components/common/FloatingInput";
import Spinner from "../../components/common/Spinner";

const LOGIN_VIEW = "login";
const FORGOT_VIEW = "forgot";
const RESET_VIEW = "reset";

function Login() {
  const [view, setView] = useState(LOGIN_VIEW);

  const [loginIdentifier, setLoginIdentifier] = useState("sandeep@test.com");
  const [password, setPassword] = useState("123456");

  const [forgotIdentifier, setForgotIdentifier] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("info");

  const navigate = useNavigate();

  function getErrorMessage(error, fallbackMessage) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item) => item?.msg || item?.message || String(item))
        .join(", ");
    }

    if (detail?.message) {
      return detail.message;
    }

    return fallbackMessage;
  }

  function showMessage(type, text) {
    setMessageType(type);
    setMessage(text);
  }

  function resetForgotForm() {
    setForgotIdentifier("");
    setOtp("");
    setNewPassword("");
    setConfirmPassword("");
  }

  function openForgotPassword() {
    setForgotIdentifier(loginIdentifier || "");
    setOtp("");
    setNewPassword("");
    setConfirmPassword("");
    setMessage("");
    setView(FORGOT_VIEW);
  }

  function backToLogin() {
    setView(LOGIN_VIEW);
    resetForgotForm();
    setMessage("");
    setMessageType("info");
  }

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
      showMessage(
        "error",
        getErrorMessage(error, "Login failed. Please check details.")
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleRequestOtp(event) {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const response = await requestForgotPasswordOtp({
        login_identifier: forgotIdentifier
      });

      showMessage(
        "success",
        response.data?.message ||
          "OTP sent to your connected Telegram. OTP is valid for 5 minutes."
      );

      setView(RESET_VIEW);
    } catch (error) {
      showMessage(
        "error",
        getErrorMessage(error, "Unable to send OTP. Please try again.")
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleResetPassword(event) {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const response = await resetPasswordWithOtp({
        login_identifier: forgotIdentifier,
        otp,
        new_password: newPassword,
        confirm_password: confirmPassword
      });

      showMessage(
        "success",
        response.data?.message || "Password reset successfully. Please login."
      );

      setPassword("");
      setLoginIdentifier(forgotIdentifier);
      setView(LOGIN_VIEW);
      setOtp("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error) {
      showMessage(
        "error",
        getErrorMessage(error, "Unable to reset password. Please try again.")
      );
    } finally {
      setLoading(false);
    }
  }

  const messageClassName =
    messageType === "success"
      ? "border-emerald-500/30 bg-emerald-950/30 text-emerald-200"
      : messageType === "error"
        ? "border-red-500/30 bg-red-950/30 text-red-200"
        : "border-oa-border bg-black text-oa-muted";

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

        {view === LOGIN_VIEW && (
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
                  onClick={openForgotPassword}
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
        )}

        {view === FORGOT_VIEW && (
          <form onSubmit={handleRequestOtp} className="space-y-4">
            <div>
              <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-white">
                <RotateCcw size={15} className="text-sky-300" />
                Forgot password
              </div>
              <p className="text-xs leading-5 text-oa-muted">
                Enter your Login ID, mobile, or email. OTP will be sent to your
                connected Telegram and will be valid for 5 minutes.
              </p>
            </div>

            <FloatingInput
              id="forgot-identifier"
              name="forgotIdentifier"
              label="Login ID / Mobile / Email"
              type="text"
              value={forgotIdentifier}
              onChange={(event) => setForgotIdentifier(event.target.value)}
              icon={UserRound}
              autoComplete="username"
              required
              variant="auth"
            />

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={backToLogin}
                disabled={loading}
                className="flex h-10 items-center justify-center gap-2 rounded-lg border border-oa-border bg-black text-sm font-semibold text-oa-muted transition hover:bg-oa-panel hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                <X size={15} />
                Cancel
              </button>

              <button
                type="submit"
                disabled={loading}
                className="flex h-10 items-center justify-center rounded-lg bg-white text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <Spinner size="sm" color="dark" />
                    Sending
                  </span>
                ) : (
                  "Send OTP"
                )}
              </button>
            </div>
          </form>
        )}

        {view === RESET_VIEW && (
          <form onSubmit={handleResetPassword} className="space-y-4">
            <div>
              <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-white">
                <KeyRound size={15} className="text-emerald-300" />
                Reset password
              </div>
              <p className="text-xs leading-5 text-oa-muted">
                Enter the OTP received on Telegram and create a new password.
              </p>
            </div>

            <FloatingInput
              id="reset-identifier"
              name="forgotIdentifier"
              label="Login ID / Mobile / Email"
              type="text"
              value={forgotIdentifier}
              onChange={(event) => setForgotIdentifier(event.target.value)}
              icon={UserRound}
              autoComplete="username"
              required
              variant="auth"
            />

            <FloatingInput
              id="reset-otp"
              name="otp"
              label="Telegram OTP"
              type="text"
              value={otp}
              onChange={(event) => setOtp(event.target.value)}
              icon={CheckCircle2}
              autoComplete="one-time-code"
              required
              variant="auth"
            />

            <FloatingInput
              id="reset-new-password"
              name="newPassword"
              label="New Password"
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              icon={Lock}
              autoComplete="new-password"
              required
              variant="auth"
            />

            <FloatingInput
              id="reset-confirm-password"
              name="confirmPassword"
              label="Confirm Password"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              icon={Lock}
              autoComplete="new-password"
              required
              variant="auth"
            />

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={backToLogin}
                disabled={loading}
                className="flex h-10 items-center justify-center gap-2 rounded-lg border border-oa-border bg-black text-sm font-semibold text-oa-muted transition hover:bg-oa-panel hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                <X size={15} />
                Cancel
              </button>

              <button
                type="submit"
                disabled={loading}
                className="flex h-10 items-center justify-center rounded-lg bg-white text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <Spinner size="sm" color="dark" />
                    Resetting
                  </span>
                ) : (
                  "Reset Password"
                )}
              </button>
            </div>

            <button
              type="button"
              onClick={handleRequestOtp}
              disabled={loading || !forgotIdentifier}
              className="w-full text-center text-xs text-oa-muted transition hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              Resend OTP
            </button>
          </form>
        )}

        {message && (
          <div
            className={`mt-3 rounded-lg border px-3 py-2 text-xs ${messageClassName}`}
          >
            {message}
          </div>
        )}
      </div>
    </div>
  );
}

export default Login;