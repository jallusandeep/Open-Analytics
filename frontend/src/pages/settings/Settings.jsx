import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Check,
  Copy,
  ExternalLink,
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
import DataTable from "../../components/tables/DataTable";
import TableToolbar from "../../components/tables/TableToolbar";
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
import {
  getMyTelegramConnection,
  startMyTelegramConnection,
  testMyTelegramConnection,
  verifyMyTelegramConnection
} from "../../api/connectionApi";

const settingsColumns = [
  { key: "field", label: "Field" },
  { key: "value", label: "Value" },
  { key: "group", label: "Group" }
];

const settingsGridTemplateColumns = "220px minmax(360px,1fr) 160px";

const groupFilterOptions = [
  { value: "all", label: "All Groups" },
  { value: "profile", label: "Profile" },
  { value: "access", label: "Access" },
  { value: "integrations", label: "Integrations" },
  { value: "system", label: "System" }
];

const telegramFilterOptions = [
  { value: "all", label: "All Telegram" },
  { value: "connected", label: "Connected" },
  { value: "pending", label: "Pending" },
  { value: "not_connected", label: "Not Connected" }
];

function normalizeCellValue(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }

  return String(value);
}

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

function getTelegramPill(status) {
  if (status === "connected") {
    return "border-sky-500/40 bg-sky-950/50 text-sky-200";
  }

  if (status === "pending") {
    return "border-amber-500/40 bg-amber-950/40 text-amber-200";
  }

  return "border-zinc-600 bg-zinc-900 text-zinc-200";
}

function getTelegramStatusLabel(status) {
  if (status === "connected") {
    return "connected";
  }

  if (status === "pending") {
    return "pending";
  }

  return "not connected";
}

function getErrorMessage(error, fallback) {
  const detail = error.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (detail?.message) {
    return detail.message;
  }

  if (detail?.raw?.message) {
    return detail.raw.message;
  }

  return fallback;
}

function getColumnValue(row, key) {
  return row[key];
}

function getFilterValues(rows, key) {
  const valueMap = new Map();

  rows.forEach((row) => {
    const value = normalizeCellValue(getColumnValue(row, key));
    valueMap.set(value, (valueMap.get(value) || 0) + 1);
  });

  return Array.from(valueMap.entries())
    .map(([value, count]) => ({
      label: value,
      value,
      count
    }))
    .sort((a, b) => a.label.localeCompare(b.label));
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
    <FloatingInput
      name={name}
      label={label}
      type={show ? "text" : "password"}
      value={value}
      onChange={onChange}
      autoComplete={autoComplete}
      required
      rightElement={
        <Tooltip text={show ? "Hide password" : "Show password"} side="left">
          <button
            type="button"
            onClick={onToggle}
            className="flex h-6 w-6 items-center justify-center rounded-sm bg-transparent text-oa-muted transition hover:text-white"
            aria-label={show ? "Hide password" : "Show password"}
          >
            {show ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </Tooltip>
      }
    />
  );
}

function FieldLabel({ icon: Icon, label }) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <Icon size={14} className="shrink-0 text-zinc-300" />
      <span className="truncate">{label}</span>
    </div>
  );
}

function Settings() {
  const savedUser = useMemo(() => getStoredCurrentUser(), []);
  const { showToast } = useToast();

  const [profile, setProfile] = useState(savedUser);
  const [telegram, setTelegram] = useState({
    connection_status: "not_connected",
    telegram_username: null,
    telegram_first_name: null,
    telegram_last_name: null,
    updated_at: null
  });
  const [telegramLink, setTelegramLink] = useState("");
  const [telegramBotUsername, setTelegramBotUsername] = useState("");

  const [searchText, setSearchText] = useState("");
  const [appliedSearchText, setAppliedSearchText] = useState("");
  const [groupFilter, setGroupFilter] = useState("all");
  const [telegramFilter, setTelegramFilter] = useState("all");

  const [columnFilters, setColumnFilters] = useState({});
  const [draftColumnFilters, setDraftColumnFilters] = useState({});
  const [activeFilter, setActiveFilter] = useState(null);

  const [sortConfig, setSortConfig] = useState({
    key: null,
    direction: null
  });

  const [loading, setLoading] = useState(false);
  const [loadingTelegram, setLoadingTelegram] = useState(false);
  const [startingTelegram, setStartingTelegram] = useState(false);
  const [verifyingTelegram, setVerifyingTelegram] = useState(false);
  const [testingTelegram, setTestingTelegram] = useState(false);
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

  const telegramStatus = telegram?.connection_status || "not_connected";
  const telegramConnected = telegramStatus === "connected";
  const updatedAtValue =
    profile?.updated_at || profile?.modified_at || profile?.created_at;

  const settingsRows = useMemo(() => {
    const telegramName = telegram?.telegram_username
      ? `@${telegram.telegram_username}`
      : telegram?.telegram_first_name || "";

    return [
      {
        id: "full_name",
        icon: User,
        field: "Full Name",
        value: profile?.full_name || "--",
        group: "Profile",
        groupKey: "profile",
        type: "text"
      },
      {
        id: "email",
        icon: Mail,
        field: "Email ID",
        value: profile?.email || "--",
        group: "Profile",
        groupKey: "profile",
        type: "text"
      },
      {
        id: "mobile_number",
        icon: Phone,
        field: "Mobile",
        value: profile?.mobile_number || "--",
        group: "Profile",
        groupKey: "profile",
        type: "text"
      },
      {
        id: "role",
        icon: Shield,
        field: "Role",
        value: formatRoleLabel(profile?.role),
        group: "Access",
        groupKey: "access",
        type: "role",
        rawRole: profile?.role
      },
      {
        id: "status",
        icon: Check,
        field: "Status",
        value: profile?.is_active === false ? "inactive" : "active",
        group: "Access",
        groupKey: "access",
        type: "status",
        isActive: profile?.is_active !== false
      },
      {
        id: "telegram",
        icon: Send,
        field: "Telegram",
        value: getTelegramStatusLabel(telegramStatus),
        group: "Integrations",
        groupKey: "integrations",
        type: "telegram",
        telegramName,
        telegramUpdatedAt: telegram?.updated_at || ""
      },
      {
        id: "login_id",
        icon: KeyRound,
        field: "Login ID",
        value: profile?.login_id || "--",
        group: "System",
        groupKey: "system",
        type: "text"
      },
      {
        id: "updated_at",
        icon: RefreshCcw,
        field: "Updated At",
        value: formatDateTime(updatedAtValue),
        group: "System",
        groupKey: "system",
        type: "text"
      }
    ];
  }, [profile, telegram, telegramStatus, updatedAtValue]);

  const headerValues = useMemo(() => {
    return settingsColumns.reduce((result, column) => {
      result[column.key] = getFilterValues(settingsRows, column.key);
      return result;
    }, {});
  }, [settingsRows]);

  const filteredRows = useMemo(() => {
    let result = settingsRows;
    const query = appliedSearchText.trim().toLowerCase();

    if (query) {
      result = result.filter((row) => {
        const values = [
          row.field,
          row.value,
          row.group,
          row.telegramName,
          row.telegramUpdatedAt
        ];

        return values.some((value) =>
          String(value || "")
            .toLowerCase()
            .includes(query)
        );
      });
    }

    if (groupFilter !== "all") {
      result = result.filter((row) => row.groupKey === groupFilter);
    }

    if (telegramFilter !== "all") {
      result = result.filter((row) => {
        if (row.id !== "telegram") {
          return false;
        }

        return telegramStatus === telegramFilter;
      });
    }

    result = result.filter((row) => {
      return Object.entries(columnFilters).every(([key, selectedValues]) => {
        if (!selectedValues || selectedValues.length === 0) {
          return true;
        }

        const value = normalizeCellValue(getColumnValue(row, key));
        return selectedValues.includes(value);
      });
    });

    if (sortConfig.key && sortConfig.direction) {
      result = [...result].sort((a, b) => {
        const firstValue = normalizeCellValue(
          getColumnValue(a, sortConfig.key)
        ).toLowerCase();

        const secondValue = normalizeCellValue(
          getColumnValue(b, sortConfig.key)
        ).toLowerCase();

        if (firstValue < secondValue) {
          return sortConfig.direction === "asc" ? -1 : 1;
        }

        if (firstValue > secondValue) {
          return sortConfig.direction === "asc" ? 1 : -1;
        }

        return 0;
      });
    }

    return result;
  }, [
    settingsRows,
    appliedSearchText,
    groupFilter,
    telegramFilter,
    telegramStatus,
    columnFilters,
    sortConfig
  ]);

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

  async function loadTelegram({ silent = false } = {}) {
    if (!silent) {
      setLoadingTelegram(true);
    }

    try {
      const response = await getMyTelegramConnection();

      setTelegram({
        connection_status: response.data?.connection_status || "not_connected",
        telegram_username: response.data?.telegram_username || null,
        telegram_first_name: response.data?.telegram_first_name || null,
        telegram_last_name: response.data?.telegram_last_name || null,
        updated_at: response.data?.updated_at || null
      });
    } catch (error) {
      const message = getErrorMessage(
        error,
        "Unable to load Telegram connection."
      );

      if (!silent) {
        showToast(message, "error");
      }
    } finally {
      if (!silent) {
        setLoadingTelegram(false);
      }
    }
  }

  async function loadAll({ silent = false } = {}) {
    await Promise.all([loadProfile({ silent }), loadTelegram({ silent })]);
  }

  useEffect(() => {
    loadAll();

    function handleWindowFocus() {
      loadAll({ silent: true });
    }

    function handleVisibilityChange() {
      if (!document.hidden) {
        loadAll({ silent: true });
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

  function hasAnyActiveFilter() {
    return (
      appliedSearchText.trim() !== "" ||
      groupFilter !== "all" ||
      telegramFilter !== "all" ||
      sortConfig.key !== null ||
      Object.values(columnFilters).some(
        (value) => Array.isArray(value) && value.length > 0
      )
    );
  }

  function clearAllFilters() {
    setSearchText("");
    setAppliedSearchText("");
    setGroupFilter("all");
    setTelegramFilter("all");
    setColumnFilters({});
    setDraftColumnFilters({});
    setSortConfig({
      key: null,
      direction: null
    });
    setActiveFilter(null);
  }

  function clearSearchFilter() {
    setSearchText("");
    setAppliedSearchText("");
  }

  function clearGroupFilter() {
    setGroupFilter("all");
  }

  function clearTelegramFilter() {
    setTelegramFilter("all");
  }

  function openColumnFilter(key) {
    setDraftColumnFilters((previous) => ({
      ...previous,
      [key]: columnFilters[key] || []
    }));

    setActiveFilter((previous) => {
      if (previous === key) {
        return null;
      }

      return key;
    });
  }

  function applyColumnFilter(key) {
    setColumnFilters((previous) => ({
      ...previous,
      [key]: draftColumnFilters[key] || []
    }));

    setActiveFilter(null);
  }

  function clearColumnFilter(key) {
    setColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setDraftColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setActiveFilter(null);
  }

  function handleSort(key, direction) {
    setSortConfig({
      key,
      direction
    });

    setActiveFilter(null);
  }

  function isColumnFilterActive(key) {
    const selectedValues = columnFilters[key] || [];
    return selectedValues.length > 0;
  }

  function handleSearchSubmit(event) {
    event.preventDefault();
    setAppliedSearchText(searchText.trim());
  }

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

  async function handleStartTelegram() {
    setStartingTelegram(true);
    setActionMessage("");

    try {
      const response = await startMyTelegramConnection();
      const url = response.data?.telegram_url || "";

      setTelegramLink(url);
      setTelegramBotUsername(response.data?.bot_username || "");
      setTelegram((previous) => ({
        ...previous,
        connection_status: response.data?.connection_status || "pending"
      }));

      showToast(response.data?.message || "Telegram link generated.", "success");

      if (url) {
        window.open(url, "_blank", "noopener,noreferrer");
      }

      await loadTelegram({ silent: true });
    } catch (error) {
      showToast(
        getErrorMessage(
          error,
          "Unable to generate Telegram connection link. Ask admin to configure Telegram bot first."
        ),
        "error"
      );
    } finally {
      setStartingTelegram(false);
    }
  }

  async function handleVerifyTelegram() {
    setVerifyingTelegram(true);
    setActionMessage("");

    try {
      const response = await verifyMyTelegramConnection();

      setTelegram({
        connection_status: response.data?.connection_status || "connected",
        telegram_username: response.data?.telegram_username || null,
        telegram_first_name: response.data?.telegram_first_name || null,
        telegram_last_name: response.data?.telegram_last_name || null,
        updated_at: response.data?.updated_at || null
      });

      setTelegramLink("");
      setTelegramBotUsername("");

      showToast(
        response.data?.message || "Telegram connected successfully.",
        "success"
      );
    } catch (error) {
      showToast(
        getErrorMessage(
          error,
          "Telegram start message was not found. Open the Telegram link, tap Start, then verify again."
        ),
        "error"
      );
    } finally {
      setVerifyingTelegram(false);
    }
  }

  async function handleTestTelegram() {
    if (!telegramConnected) {
      showToast("Telegram is not connected yet.", "warning");
      return;
    }

    setTestingTelegram(true);

    try {
      const response = await testMyTelegramConnection();

      showToast(
        response.data?.message || "Telegram test message sent successfully.",
        "success"
      );
    } catch (error) {
      showToast(
        getErrorMessage(error, "Unable to send Telegram test message."),
        "error"
      );
    } finally {
      setTestingTelegram(false);
    }
  }

  async function handleCopyTelegramLink() {
    if (!telegramLink) {
      showToast("Generate Telegram link first.", "warning");
      return;
    }

    try {
      await navigator.clipboard.writeText(telegramLink);
      showToast("Telegram link copied.", "success");
    } catch {
      showToast("Unable to copy Telegram link.", "error");
    }
  }

  function renderCell(row, column) {
    if (column.key === "field") {
      return <FieldLabel icon={row.icon} label={row.field} />;
    }

    if (column.key === "group") {
      return <span className="truncate text-oa-muted">{row.group}</span>;
    }

    if (row.type === "role") {
      return (
        <span className={`${oaPillStyles.base} ${getRolePill(row.rawRole)}`}>
          {row.value}
        </span>
      );
    }

    if (row.type === "status") {
      return (
        <span className={`${oaPillStyles.base} ${getStatusPill(row.isActive)}`}>
          {row.value}
        </span>
      );
    }

    if (row.type === "telegram") {
      return (
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className={`${oaPillStyles.base} ${getTelegramPill(telegramStatus)}`}>
            {getTelegramStatusLabel(telegramStatus)}
          </span>

          {loadingTelegram ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-normal text-oa-muted">
              <Spinner size="xs" color="light" />
              checking
            </span>
          ) : null}

          {row.telegramName ? (
            <span className="truncate text-[12px] font-normal text-oa-muted">
              {row.telegramName}
            </span>
          ) : null}

          {row.telegramUpdatedAt ? (
            <span className="truncate text-[11px] font-normal text-oa-muted">
              {formatDateTime(row.telegramUpdatedAt)}
            </span>
          ) : null}

          {telegramBotUsername && !telegramConnected ? (
            <span className="truncate text-[11px] font-normal text-oa-muted">
              Bot: @{telegramBotUsername}
            </span>
          ) : null}

          <button
            type="button"
            disabled={startingTelegram}
            onClick={handleStartTelegram}
            className="ml-1 rounded border border-sky-500/30 bg-sky-950/20 px-2.5 py-1 text-[11px] font-semibold text-sky-300 transition hover:border-sky-500/60 hover:bg-sky-950/40 hover:text-sky-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {startingTelegram ? "Opening..." : telegramConnected ? "Reconnect" : "Connect"}
          </button>

          <button
            type="button"
            disabled={verifyingTelegram}
            onClick={handleVerifyTelegram}
            className="rounded border border-emerald-500/30 bg-emerald-950/20 px-2.5 py-1 text-[11px] font-semibold text-emerald-300 transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {verifyingTelegram ? "Verifying..." : "Verify"}
          </button>

          <button
            type="button"
            disabled={!telegramConnected || testingTelegram}
            onClick={handleTestTelegram}
            className="rounded border border-oa-border bg-black px-2.5 py-1 text-[11px] font-semibold text-oa-muted transition hover:bg-oa-card hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {testingTelegram ? "Testing..." : "Test"}
          </button>
        </div>
      );
    }

    return <span className="truncate text-oa-text">{row.value}</span>;
  }

  return (
    <MainLayout>
      <section className="min-h-screen bg-black p-3">
        <div className="space-y-3">
          <div className={oaCardStyles.wrapper}>
            <div className={oaCardStyles.header}>
              <h2 className={oaCardStyles.headerTitle}>Settings</h2>
            </div>

            <div className="border-b border-oa-border bg-black px-3 py-1.5 [&>div]:mb-0">
              <TableToolbar
                searchValue={searchText}
                onSearchChange={setSearchText}
                onSearchClear={clearSearchFilter}
                onSearchSubmit={handleSearchSubmit}
                searchActive={appliedSearchText.trim() !== ""}
                searchPlaceholder="Search settings"
                filters={[
                  {
                    value: groupFilter,
                    onChange: (event) => setGroupFilter(event.target.value),
                    options: groupFilterOptions,
                    onClear: clearGroupFilter,
                    showClear: groupFilter !== "all",
                    ariaLabel: "Group filter",
                    minWidth: "w-40"
                  },
                  {
                    value: telegramFilter,
                    onChange: (event) => setTelegramFilter(event.target.value),
                    options: telegramFilterOptions,
                    onClear: clearTelegramFilter,
                    showClear: telegramFilter !== "all",
                    ariaLabel: "Telegram filter",
                    minWidth: "w-40"
                  }
                ]}
                hasActiveFilter={hasAnyActiveFilter()}
                onClearAll={clearAllFilters}
                loading={loading || loadingTelegram}
                rightActions={[
                  {
                    icon: RefreshCcw,
                    label: "Refresh",
                    variant: "refresh",
                    disabled: loading || loadingTelegram,
                    onClick: () => loadAll()
                  },
                  {
                    icon: Pencil,
                    label: "Edit Details",
                    variant: "default",
                    disabled: loading || !profile,
                    onClick: openDetailsModal
                  },
                  {
                    icon: LockKeyhole,
                    label: "Change Password",
                    variant: "add",
                    onClick: openPasswordModal
                  }
                ]}
              />
            </div>

            {actionMessage && (
              <div
                className={`flex items-center gap-2 border-b border-oa-border bg-black px-3 py-2 ${oaTableStyles.mutedText}`}
              >
                <AlertCircle size={15} className="text-amber-300" />
                <span>{actionMessage}</span>
              </div>
            )}

            {telegramLink && !telegramConnected ? (
              <div className="border-b border-oa-border bg-black px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-oa-muted">
                      Telegram Link
                    </p>
                    <p className="mt-1 truncate text-[12px] text-oa-text">
                      {telegramLink}
                    </p>
                  </div>

                  <IconButton
                    icon={Copy}
                    label="Copy Telegram Link"
                    variant="default"
                    onClick={handleCopyTelegramLink}
                    tooltipSide="top"
                  />

                  <a
                    href={telegramLink}
                    target="_blank"
                    rel="noreferrer"
                    className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-oa-muted outline-none transition hover:bg-oa-card hover:text-white focus:border-oa-muted"
                    aria-label="Open Telegram Link"
                    title="Open Telegram Link"
                  >
                    <ExternalLink size={15} />
                  </a>
                </div>

                <p className="mt-2 text-[11px] leading-5 text-oa-muted">
                  Open this link, tap Start in Telegram, then come back and click
                  Verify.
                </p>
              </div>
            ) : null}

            <div className="overflow-x-auto bg-black [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
              <DataTable
                columns={settingsColumns}
                rows={filteredRows}
                loading={loading && !profile}
                loadingMessage="Loading user details"
                emptyMessage="No settings found."
                gridTemplateColumns={settingsGridTemplateColumns}
                minWidth="min-w-[900px]"
                getRowKey={(row) => row.id}
                renderCell={renderCell}
                filterConfig={{
                  activeFilter,
                  headerValues,
                  columnFilters,
                  draftColumnFilters,
                  rightAlignedKeys: ["group"],
                  isColumnFilterActive,
                  onOpen: openColumnFilter,
                  onClose: () => setActiveFilter(null),
                  onChange: (key, values) =>
                    setDraftColumnFilters((previous) => ({
                      ...previous,
                      [key]: values
                    })),
                  onApply: applyColumnFilter,
                  onSort: handleSort,
                  onClear: clearColumnFilter
                }}
              />
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

            <IconButton
              icon={Check}
              label="Update details"
              type="submit"
              form="edit-details-form"
              variant="add"
              tooltipSide="top"
              loading={updatingDetails}
              iconSize={15}
            />
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

            <IconButton
              icon={Check}
              label="Update password"
              type="submit"
              form="change-password-form"
              variant="add"
              tooltipSide="top"
              loading={savingPassword}
              iconSize={15}
            />
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
