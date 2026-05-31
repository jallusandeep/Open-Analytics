import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Check,
  Eye,
  EyeOff,
  KeyRound,
  LockKeyhole,
  Mail,
  Pencil,
  Phone,
  RefreshCcw,
  Send,
  Shield,
  User,
  X
} from "lucide-react";

import MainLayout from "../../components/layout/MainLayout";
import Spinner from "../../components/common/Spinner";
import IconButton from "../../components/common/IconButton";
import FloatingInput from "../../components/common/FloatingInput";
import Modal from "../../components/common/Modal";
import Tooltip from "../../components/common/Tooltip";
import { useToast } from "../../components/common/ToastProvider";
import {
  oaCardStyles,
  oaFormTextStyles,
  oaPillStyles,
  oaTableStyles
} from "../../components/common/uiStyles";
import {
  changeMyPassword,
  getMyProfile,
  updateMyProfile
} from "../../api/settingsApi";

function formatRoleLabel(role) {
  if (!role) {
    return "--";
  }

  return String(role)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDateTime(value) {
  if (!value) {
    return "--";
  }

  const parsedDate = new Date(value);

  if (Number.isNaN(parsedDate.getTime())) {
    return String(value);
  }

  return parsedDate.toLocaleString();
}

function getStoredCurrentUser() {
  try {
    const currentUser =
      localStorage.getItem("open_analytics_current_user") ||
      localStorage.getItem("open_analytics_user");

    if (!currentUser) {
      return null;
    }

    return JSON.parse(currentUser);
  } catch {
    return null;
  }
}

function getStatusPill(isActive) {
  return isActive
    ? "border-emerald-500/40 bg-emerald-950/50 text-emerald-200"
    : "border-red-500/40 bg-red-950/50 text-red-200";
}

function getRolePill(role) {
  const roleClass = {
    super_admin: "border-purple-500/40 bg-purple-950/50 text-purple-200",
    admin: "border-sky-500/40 bg-sky-950/50 text-sky-200",
    user: "border-zinc-600 bg-zinc-900 text-zinc-200"
  };

  return roleClass[role] || roleClass.user;
}

function getTelegramPill(isConnected) {
  return isConnected
    ? "border-sky-500/40 bg-sky-950/50 text-sky-200"
    : "border-zinc-600 bg-zinc-900 text-zinc-200";
}

function PasswordFloatingInput({
  name,
  label,
  value,
  onChange,
  show,
  onToggle,
  autoComplete
}) {
  return (
    <div className="relative">
      <FloatingInput
        name={name}
        label={label}
        type={show ? "text" : "password"}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        required
      />

      <div className="pointer-events-none absolute inset-y-0 right-2 flex items-center">
        <Tooltip text={show ? "Hide password" : "Show password"} side="left">
          <button
            type="button"
            onClick={onToggle}
            className="pointer-events-auto flex h-7 w-7 items-center justify-center rounded-sm text-oa-muted transition hover:bg-oa-card hover:text-white"
            aria-label={show ? "Hide password" : "Show password"}
          >
            {show ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </Tooltip>
      </div>
    </div>
  );
}

function ProfileRow({ icon: Icon, label, children }) {
  return (
    <div className="grid grid-cols-[150px_1fr] items-center border-b border-oa-border px-3 py-2 text-[13px] last:border-b-0 hover:bg-oa-panel/60">
      <div className="flex min-w-0 items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-oa-muted">
        <Icon size={14} className="shrink-0 text-zinc-300" />
        <span className="truncate">{label}</span>
      </div>

      <div className="min-w-0 text-[13px] font-semibold text-oa-text">
        {children}
      </div>
    </div>
  );
}

function Settings() {
  const savedUser = useMemo(() => getStoredCurrentUser(), []);
  const { showToast } = useToast();

  const [profile, setProfile] = useState(savedUser);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState("");

  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [updatingDetails, setUpdatingDetails] = useState(false);
  const [detailsForm, setDetailsForm] = useState({
    full_name: "",
    email: "",
    mobile_number: ""
  });

  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: ""
  });

  const [showPassword, setShowPassword] = useState({
    current: false,
    new: false,
    confirm: false
  });

  function saveUserToStorage(user) {
    if (!user) {
      return;
    }

    localStorage.setItem("open_analytics_current_user", JSON.stringify(user));
    localStorage.setItem("open_analytics_user", JSON.stringify(user));
  }

  async function loadProfile({ silent = false } = {}) {
    if (!silent) {
      setLoading(true);
    }

    setActionMessage("");

    try {
      const response = await getMyProfile();
      const user = response.data?.user || response.data;

      setProfile(user);
      saveUserToStorage(user);
    } catch (error) {
      const message =
        error.response?.data?.detail ||
        "Unable to load latest user details. Showing saved details.";

      setActionMessage(message);

      if (!silent) {
        showToast(message, "error");
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    loadProfile();

    function handleWindowFocus() {
      loadProfile({ silent: true });
    }

    function handleVisibilityChange() {
      if (!document.hidden) {
        loadProfile({ silent: true });
      }
    }

    window.addEventListener("focus", handleWindowFocus);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.removeEventListener("focus", handleWindowFocus);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function openDetailsModal() {
    setActionMessage("");
    setDetailsForm({
      full_name: profile?.full_name || "",
      email: profile?.email || "",
      mobile_number: profile?.mobile_number || ""
    });
    setShowDetailsModal(true);
  }

  function closeDetailsModal() {
    if (updatingDetails) {
      return;
    }

    setShowDetailsModal(false);
    setDetailsForm({
      full_name: "",
      email: "",
      mobile_number: ""
    });
  }

  function handleDetailsInputChange(event) {
    const { name, value } = event.target;

    setActionMessage("");

    setDetailsForm((previous) => ({
      ...previous,
      [name]: value
    }));
  }

  async function handleUpdateDetails(event) {
    event.preventDefault();

    const fullName = detailsForm.full_name.trim();
    const email = detailsForm.email.trim().toLowerCase();
    const mobileNumber = detailsForm.mobile_number.trim();

    if (fullName.length < 2) {
      showToast("Full name must be at least 2 characters.", "error");
      return;
    }

    if (!email) {
      showToast("Email ID is required.", "error");
      return;
    }

    setUpdatingDetails(true);
    setActionMessage("");

    try {
      const response = await updateMyProfile({
        full_name: fullName,
        email,
        mobile_number: mobileNumber || null
      });

      const updatedUser = response.data?.user;

      if (updatedUser) {
        setProfile(updatedUser);
        saveUserToStorage(updatedUser);
      } else {
        await loadProfile({ silent: true });
      }

      setShowDetailsModal(false);
      setDetailsForm({
        full_name: "",
        email: "",
        mobile_number: ""
      });

      showToast(
        response.data?.message || "User details updated successfully.",
        "success"
      );
    } catch (error) {
      showToast(
        error.response?.data?.detail ||
          "Unable to update user details. Please try again.",
        "error"
      );
    } finally {
      setUpdatingDetails(false);
    }
  }

  function openPasswordModal() {
    setActionMessage("");
    setShowPasswordModal(true);
  }

  function closePasswordModal() {
    if (savingPassword) {
      return;
    }

    clearPasswordForm(false);
    setShowPasswordModal(false);
  }

  function handlePasswordInputChange(event) {
    const { name, value } = event.target;

    setActionMessage("");

    setPasswordForm((previous) => ({
      ...previous,
      [name]: value
    }));
  }

  function clearPasswordForm(clearMessage = true) {
    setPasswordForm({
      current_password: "",
      new_password: "",
      confirm_password: ""
    });

    setShowPassword({
      current: false,
      new: false,
      confirm: false
    });

    if (clearMessage) {
      setActionMessage("");
    }
  }

  async function handleChangePassword(event) {
    event.preventDefault();

    const currentPassword = passwordForm.current_password.trim();
    const newPassword = passwordForm.new_password.trim();
    const confirmPassword = passwordForm.confirm_password.trim();

    if (!currentPassword || !newPassword || !confirmPassword) {
      showToast("Please fill all password fields.", "error");
      return;
    }

    if (newPassword.length < 6) {
      showToast("New password must be at least 6 characters.", "error");
      return;
    }

    if (newPassword !== confirmPassword) {
      showToast("New password and confirm password do not match.", "error");
      return;
    }

    if (currentPassword === newPassword) {
      showToast("New password must be different from current password.", "error");
      return;
    }

    setSavingPassword(true);
    setActionMessage("");

    try {
      const response = await changeMyPassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword
      });

      clearPasswordForm(false);
      setShowPasswordModal(false);

      showToast(
        response.data?.message || "Password changed successfully.",
        "success"
      );
    } catch (error) {
      showToast(
        error.response?.data?.detail ||
          "Unable to change password. Please try again.",
        "error"
      );
    } finally {
      setSavingPassword(false);
    }
  }

  const telegramConnected = Boolean(profile?.telegram_connected);
  const updatedAtValue =
    profile?.updated_at || profile?.modified_at || profile?.created_at;

  return (
    <MainLayout>
      <section className="min-h-screen bg-black p-3">
        <div className="space-y-3">
          <div className={oaCardStyles.wrapper}>
            <div className={oaCardStyles.header}>
              <h2 className={oaCardStyles.headerTitle}>Settings</h2>
            </div>

            <div className="border-b border-oa-border bg-black px-3 py-1.5">
              <div className="flex items-center justify-start gap-2">
                <IconButton
                  icon={RefreshCcw}
                  label="Refresh"
                  variant="refresh"
                  disabled={loading}
                  onClick={() => loadProfile()}
                  tooltipSide="right"
                />

                <IconButton
                  icon={Pencil}
                  label="Edit Details"
                  variant="default"
                  disabled={loading || !profile}
                  onClick={openDetailsModal}
                  tooltipSide="right"
                />

                <IconButton
                  icon={LockKeyhole}
                  label="Change Password"
                  variant="add"
                  onClick={openPasswordModal}
                  tooltipSide="right"
                />
              </div>
            </div>

            {actionMessage && (
              <div
                className={`flex items-center gap-2 border-b border-oa-border bg-black px-3 py-2 ${oaTableStyles.mutedText}`}
              >
                <AlertCircle size={15} className="text-amber-300" />
                <span>{actionMessage}</span>
              </div>
            )}

            <div className="overflow-x-auto bg-black oa-table-font [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
              <div className="min-w-[720px]">
                <div className="grid rounded-t border-b border-oa-border bg-oa-panel px-3 py-2.5 text-[11px] font-bold uppercase tracking-wider text-oa-muted">
                  <span>User Details</span>
                </div>

                {loading && !profile ? (
                  <div className="flex min-h-[230px] items-center justify-center gap-2 border-b border-oa-border text-[12px] text-oa-muted">
                    <Spinner size="xs" color="light" />
                    <span>Loading user details</span>
                  </div>
                ) : (
                  <div className="bg-black">
                    <ProfileRow icon={User} label="Full Name">
                      <span className="truncate">
                        {profile?.full_name || "--"}
                      </span>
                    </ProfileRow>

                    <ProfileRow icon={Mail} label="Email ID">
                      <span className="truncate">{profile?.email || "--"}</span>
                    </ProfileRow>

                    <ProfileRow icon={Phone} label="Mobile">
                      <span className="truncate">
                        {profile?.mobile_number || "--"}
                      </span>
                    </ProfileRow>

                    <ProfileRow icon={Shield} label="Role">
                      <span
                        className={`${oaPillStyles.base} ${getRolePill(
                          profile?.role
                        )}`}
                      >
                        {formatRoleLabel(profile?.role)}
                      </span>
                    </ProfileRow>

                    <ProfileRow icon={Check} label="Status">
                      <span
                        className={`${oaPillStyles.base} ${getStatusPill(
                          profile?.is_active !== false
                        )}`}
                      >
                        {profile?.is_active === false ? "inactive" : "active"}
                      </span>
                    </ProfileRow>

                    <ProfileRow icon={Send} label="Telegram">
                      <span
                        className={`${oaPillStyles.base} ${getTelegramPill(
                          telegramConnected
                        )}`}
                      >
                        {telegramConnected ? "connected" : "not connected"}
                      </span>
                    </ProfileRow>

                    <ProfileRow icon={KeyRound} label="Login ID">
                      <span className="truncate">
                        {profile?.login_id || "--"}
                      </span>
                    </ProfileRow>

                    <ProfileRow icon={RefreshCcw} label="Updated At">
                      <span className="truncate">
                        {formatDateTime(updatedAtValue)}
                      </span>
                    </ProfileRow>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      <Modal
        open={showDetailsModal}
        title="Edit Details"
        onClose={closeDetailsModal}
        width="max-w-md"
        closeOnOverlay={!updatingDetails}
        footer={
          <>
            <IconButton
              icon={X}
              label="Cancel"
              variant="danger"
              tooltipSide="top"
              disabled={updatingDetails}
              onClick={closeDetailsModal}
            />

            <Tooltip text="Update details" side="top">
              <button
                type="submit"
                form="edit-details-form"
                disabled={updatingDetails}
                className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                aria-label="Update details"
              >
                {updatingDetails ? (
                  <Spinner size="xs" color="light" />
                ) : (
                  <Check size={15} />
                )}
              </button>
            </Tooltip>
          </>
        }
      >
        <form id="edit-details-form" onSubmit={handleUpdateDetails}>
          <div className="grid gap-3">
            <FloatingInput
              name="full_name"
              label="Full Name"
              value={detailsForm.full_name}
              onChange={handleDetailsInputChange}
              required
            />

            <FloatingInput
              name="email"
              label="Email ID"
              type="email"
              value={detailsForm.email}
              onChange={handleDetailsInputChange}
              autoComplete="email"
              required
            />

            <FloatingInput
              name="mobile_number"
              label="Mobile Number"
              value={detailsForm.mobile_number}
              onChange={handleDetailsInputChange}
              autoComplete="tel"
            />
          </div>
        </form>
      </Modal>

      <Modal
        open={showPasswordModal}
        title="Change Password"
        onClose={closePasswordModal}
        width="max-w-md"
        closeOnOverlay={!savingPassword}
        footer={
          <>
            <IconButton
              icon={X}
              label="Cancel"
              variant="danger"
              tooltipSide="top"
              disabled={savingPassword}
              onClick={closePasswordModal}
            />

            <Tooltip text="Update password" side="top">
              <button
                type="submit"
                form="change-password-form"
                disabled={savingPassword}
                className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                aria-label="Update password"
              >
                {savingPassword ? (
                  <Spinner size="xs" color="light" />
                ) : (
                  <Check size={15} />
                )}
              </button>
            </Tooltip>
          </>
        }
      >
        <form id="change-password-form" onSubmit={handleChangePassword}>
          <div className="grid gap-3">
            <PasswordFloatingInput
              name="current_password"
              label="Current Password"
              value={passwordForm.current_password}
              onChange={handlePasswordInputChange}
              show={showPassword.current}
              onToggle={() =>
                setShowPassword((previous) => ({
                  ...previous,
                  current: !previous.current
                }))
              }
              autoComplete="current-password"
            />

            <PasswordFloatingInput
              name="new_password"
              label="New Password"
              value={passwordForm.new_password}
              onChange={handlePasswordInputChange}
              show={showPassword.new}
              onToggle={() =>
                setShowPassword((previous) => ({
                  ...previous,
                  new: !previous.new
                }))
              }
              autoComplete="new-password"
            />

            <PasswordFloatingInput
              name="confirm_password"
              label="Confirm Password"
              value={passwordForm.confirm_password}
              onChange={handlePasswordInputChange}
              show={showPassword.confirm}
              onToggle={() =>
                setShowPassword((previous) => ({
                  ...previous,
                  confirm: !previous.confirm
                }))
              }
              autoComplete="new-password"
            />
          </div>

          <div
            className={`mt-3 rounded border border-oa-border bg-oa-panel/40 px-3 py-2 ${oaFormTextStyles.helper}`}
          >
            Password must be at least 6 characters. New password must be
            different from current password.
          </div>
        </form>
      </Modal>
    </MainLayout>
  );
}

export default Settings;