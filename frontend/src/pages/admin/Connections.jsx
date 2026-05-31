import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Check,
  Copy,
  Edit3,
  ExternalLink,
  Plus,
  PlugZap,
  RefreshCcw,
  Search,
  Trash2,
  X
} from "lucide-react";

import MainLayout from "../../components/layout/MainLayout";
import Spinner from "../../components/common/Spinner";
import IconButton from "../../components/common/IconButton";
import Input from "../../components/common/Input";
import Select from "../../components/common/Select";
import Modal from "../../components/common/Modal";
import DataTable from "../../components/tables/DataTable";
import { useToast } from "../../components/common/ToastProvider";
import {
  oaCardStyles,
  oaFormTextStyles,
  oaPillStyles
} from "../../components/common/uiStyles";
import {
  disconnectUpstoxConnection,
  getConnections,
  saveUpstoxConnection,
  testUpstoxConnection
} from "../../api/connectionApi";

const emptyFormData = {
  provider: "upstox",
  api_key: "",
  api_secret: "",
  redirect_url: "",
  authorization_code: "",
  access_token: ""
};

const brokers = [
  {
    id: "upstox",
    name: "Upstox",
    description: "OAuth based broker connection.",
    apiSupported: true
  }
];

const providerOptions = brokers.map((broker) => ({
  value: broker.id,
  label: broker.name
}));

const connectionColumns = [
  { key: "provider", label: "Provider", filterable: false },
  { key: "status", label: "Status", filterable: false },
  { key: "updated_at", label: "Updated At", filterable: false },
  { key: "token_expiry", label: "Token Expiry", filterable: false },
  { key: "updated_by", label: "Updated By", filterable: false }
];

const connectionGridTemplateColumns = "1.4fr 0.9fr 1.1fr 1.1fr 1.1fr 132px";

function getStoredCurrentUser() {
  try {
    const savedUser =
      localStorage.getItem("open_analytics_current_user") ||
      localStorage.getItem("open_analytics_user");

    if (!savedUser) {
      return null;
    }

    return JSON.parse(savedUser);
  } catch {
    return null;
  }
}

function formatUserName(user) {
  if (!user) {
    return "--";
  }

  return user.full_name || user.name || user.email || user.login_id || "--";
}

function getConnectionStatus(connection) {
  if (!connection) {
    return "not_connected";
  }

  return connection.connection_status || "saved";
}

function getStatusLabel(status) {
  if (status === "connected") {
    return "Connected";
  }

  if (status === "limited") {
    return "Limited";
  }

  if (status === "failed") {
    return "Failed";
  }

  if (status === "saved") {
    return "Saved";
  }

  return "Not Connected";
}

function getStatusClass(status) {
  if (status === "connected") {
    return "border-emerald-500/40 bg-emerald-950/50 text-emerald-200";
  }

  if (status === "limited") {
    return "border-amber-500/40 bg-amber-950/40 text-amber-200";
  }

  if (status === "failed") {
    return "border-red-500/40 bg-red-950/50 text-red-200";
  }

  if (status === "saved") {
    return "border-sky-500/40 bg-sky-950/50 text-sky-200";
  }

  return "border-zinc-600 bg-zinc-900 text-zinc-200";
}

function formatDateTime(value) {
  if (!value) {
    return "--";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value).replace(/:\d{2}(\.\d+)?$/, "");
  }

  return date.toLocaleString("en-IN", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true
  });
}

function addOneYear(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  date.setFullYear(date.getFullYear() + 1);
  return date;
}

function getLastUpdated(connection) {
  return (
    connection?.updated_at ||
    connection?.last_updated_at ||
    connection?.last_tested_at ||
    connection?.created_at ||
    ""
  );
}

function getTokenExpiry(connection) {
  if (!connection) {
    return "--";
  }

  const explicitExpiry =
    connection?.token_expires_at ||
    connection?.access_token_expires_at ||
    connection?.expires_at;

  if (explicitExpiry) {
    return formatDateTime(explicitExpiry);
  }

  const lastUpdated = getLastUpdated(connection);
  const calculatedExpiry = addOneYear(lastUpdated);

  if (calculatedExpiry) {
    return formatDateTime(calculatedExpiry);
  }

  return "Valid for 1 year";
}

function buildUpstoxAuthorizationUrl(apiKey, redirectUrl) {
  const cleanApiKey = apiKey.trim();
  const cleanRedirectUrl = redirectUrl.trim();

  if (!cleanApiKey || !cleanRedirectUrl) {
    return "";
  }

  const params = new URLSearchParams({
    response_type: "code",
    client_id: cleanApiKey,
    redirect_uri: cleanRedirectUrl
  });

  return `https://api.upstox.com/v2/login/authorization/dialog?${params.toString()}`;
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

function StatusBadge({ status }) {
  return (
    <span className={`${oaPillStyles.base} ${getStatusClass(status)}`}>
      {getStatusLabel(status)}
    </span>
  );
}

function ClearInputButton({ label, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-oa-muted transition hover:bg-oa-card hover:text-white"
      aria-label={label}
    >
      <X size={13} />
    </button>
  );
}

function ConnectionFormModal({
  open,
  mode,
  formData,
  selectedConnection,
  saving,
  isAdminControlAllowed,
  onClose,
  onSave,
  onInputChange,
  onClearField,
  onCopyAuthUrl
}) {
  const title = mode === "edit" ? "Edit Connection" : "Add Connection";
  const subtitle =
    mode === "edit"
      ? "Replace the saved Upstox OAuth token."
      : "Enter Upstox app details, generate login URL, then paste the authorization code.";

  const authorizationUrl = buildUpstoxAuthorizationUrl(
    formData.api_key,
    formData.redirect_url
  );

  const hasAuthorizationCode = formData.authorization_code.trim();
  const hasAccessToken = formData.access_token.trim();

  const canSave =
    isAdminControlAllowed &&
    (hasAccessToken ||
      (formData.api_key.trim() &&
        formData.api_secret.trim() &&
        formData.redirect_url.trim() &&
        hasAuthorizationCode));

  function handleSubmit(event) {
    event.preventDefault();
    onSave();
  }

  return (
    <Modal
      open={open}
      title={title}
      subtitle={subtitle}
      onClose={onClose}
      width="max-w-2xl"
      footer={
        <div className="flex items-center justify-end gap-2">
          <IconButton
            icon={X}
            label="Cancel"
            variant="default"
            disabled={saving}
            onClick={onClose}
            tooltipSide="top"
          />

          <IconButton
            icon={Check}
            label={mode === "edit" ? "Update connection" : "Save connection"}
            variant="default"
            disabled={saving || !canSave}
            onClick={onSave}
            tooltipSide="top"
          />
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-3 oa-table-font">
        <div>
          <label className={oaFormTextStyles.label}>Provider</label>
          <div className="mt-1">
            <Select
              value={formData.provider}
              onChange={(event) =>
                onInputChange({
                  target: {
                    name: "provider",
                    value: event.target.value
                  }
                })
              }
              options={providerOptions}
              ariaLabel="Provider"
              minWidth="w-full"
              disabled={mode === "edit"}
            />
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label className={oaFormTextStyles.label}>API Key</label>
            <div className="relative mt-1">
              <Input
                name="api_key"
                type="text"
                value={formData.api_key}
                onChange={onInputChange}
                placeholder={
                  selectedConnection?.api_key
                    ? "Saved - enter to replace"
                    : "Enter Upstox API key"
                }
                className="pr-9"
              />

              {formData.api_key ? (
                <ClearInputButton
                  label="Clear API key"
                  onClick={() => onClearField("api_key")}
                />
              ) : null}
            </div>
          </div>

          <div>
            <label className={oaFormTextStyles.label}>API Secret</label>
            <div className="relative mt-1">
              <Input
                name="api_secret"
                type="password"
                value={formData.api_secret}
                onChange={onInputChange}
                placeholder={
                  selectedConnection?.has_api_secret
                    ? "Saved - enter to replace"
                    : "Enter Upstox API secret"
                }
                className="pr-9"
              />

              {formData.api_secret ? (
                <ClearInputButton
                  label="Clear API secret"
                  onClick={() => onClearField("api_secret")}
                />
              ) : null}
            </div>
          </div>
        </div>

        <div>
          <label className={oaFormTextStyles.label}>Redirect URL</label>
          <div className="relative mt-1">
            <Input
              name="redirect_url"
              type="text"
              value={formData.redirect_url}
              onChange={onInputChange}
              placeholder={
                selectedConnection?.redirect_url
                  ? selectedConnection.redirect_url
                  : "Enter the same redirect URL added in Upstox app"
              }
              className="pr-9"
            />

            {formData.redirect_url ? (
              <ClearInputButton
                label="Clear redirect URL"
                onClick={() => onClearField("redirect_url")}
              />
            ) : null}
          </div>
        </div>

        <div className="rounded border border-oa-border bg-black p-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-oa-muted">
              Upstox Login URL
            </p>

            <div className="flex items-center gap-2">
              <IconButton
                icon={Copy}
                label="Copy login URL"
                variant="default"
                disabled={!authorizationUrl}
                onClick={() => onCopyAuthUrl(authorizationUrl)}
                tooltipSide="top"
              />

              <a
                href={authorizationUrl || undefined}
                target="_blank"
                rel="noreferrer"
                className={`flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-oa-muted outline-none transition hover:bg-oa-card hover:text-white ${
                  authorizationUrl
                    ? ""
                    : "pointer-events-none cursor-not-allowed opacity-50"
                }`}
                aria-label="Open Upstox login URL"
                title="Open Upstox login URL"
              >
                <ExternalLink size={14} />
              </a>
            </div>
          </div>

          <p className="mt-2 break-all text-[11px] text-oa-muted">
            {authorizationUrl ||
              "Enter API key and redirect URL to generate login URL."}
          </p>
        </div>

        <div>
          <label className={oaFormTextStyles.label}>Authorization Code</label>
          <div className="relative mt-1">
            <Input
              name="authorization_code"
              type="password"
              value={formData.authorization_code}
              onChange={onInputChange}
              placeholder="Paste code from Upstox redirect URL"
              className="pr-9"
              autoFocus
            />

            {formData.authorization_code ? (
              <ClearInputButton
                label="Clear authorization code"
                onClick={() => onClearField("authorization_code")}
              />
            ) : null}
          </div>
        </div>

        <div className="border-t border-oa-border pt-3">
          <label className={oaFormTextStyles.label}>
            Access Token Override
          </label>
          <div className="relative mt-1">
            <Input
              name="access_token"
              type="password"
              value={formData.access_token}
              onChange={onInputChange}
              placeholder={
                selectedConnection
                  ? "Optional - paste token directly to replace"
                  : "Optional - paste token directly instead of OAuth code"
              }
              className="pr-9"
            />

            {formData.access_token ? (
              <ClearInputButton
                label="Clear access token"
                onClick={() => onClearField("access_token")}
              />
            ) : null}
          </div>
        </div>

        <button type="submit" className="hidden" aria-hidden="true">
          Submit
        </button>
      </form>
    </Modal>
  );
}

function Connections() {
  const [connections, setConnections] = useState([]);
  const [formData, setFormData] = useState(emptyFormData);
  const [formMode, setFormMode] = useState("closed");

  const [searchValue, setSearchValue] = useState("");
  const [appliedSearchValue, setAppliedSearchValue] = useState("");

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testingProvider, setTestingProvider] = useState("");
  const [disconnectingProvider, setDisconnectingProvider] = useState("");

  const { showToast } = useToast();

  const currentUser = useMemo(() => getStoredCurrentUser(), []);
  const isAdminControlAllowed = ["admin", "super_admin"].includes(
    currentUser?.role
  );

  const connectionsByProvider = useMemo(() => {
    return connections.reduce((accumulator, item) => {
      accumulator[item.provider] = item;
      return accumulator;
    }, {});
  }, [connections]);

  const rows = useMemo(() => {
    return brokers.map((broker) => {
      const connection = connectionsByProvider[broker.id] || null;

      return {
        id: broker.id,
        broker,
        connection,
        provider: broker.name,
        description: broker.description,
        status: getConnectionStatus(connection),
        updated_at: getLastUpdated(connection),
        token_expiry: getTokenExpiry(connection),
        updated_by: connection ? formatUserName(currentUser) : "--"
      };
    });
  }, [connectionsByProvider, currentUser]);

  const filteredRows = useMemo(() => {
    const query = appliedSearchValue.trim().toLowerCase();

    if (!query) {
      return rows;
    }

    return rows.filter((row) => {
      const values = [
        row.provider,
        row.description,
        getStatusLabel(row.status),
        formatDateTime(row.updated_at),
        row.token_expiry,
        row.updated_by
      ];

      return values.some((value) => String(value).toLowerCase().includes(query));
    });
  }, [rows, appliedSearchValue]);

  const formBroker = useMemo(() => {
    return brokers.find((item) => item.id === formData.provider) || brokers[0];
  }, [formData.provider]);

  const selectedConnection = connectionsByProvider[formData.provider] || null;
  const formOpen = formMode !== "closed";

  async function loadConnections(showRefreshToast = false) {
    setLoading(true);

    try {
      const response = await getConnections();
      setConnections(response.data.connections || []);

      if (showRefreshToast) {
        showToast("Connections refreshed successfully.", "success");
      }
    } catch (error) {
      showToast(getErrorMessage(error, "Unable to load connections."), "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadConnections(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function openAddForm() {
    setFormMode("add");
    setFormData(emptyFormData);
  }

  function openEditForm(provider) {
    const connection = connectionsByProvider[provider] || null;

    setFormMode("edit");
    setFormData({
      provider,
      api_key: connection?.api_key || "",
      api_secret: "",
      redirect_url: connection?.redirect_url || "",
      authorization_code: "",
      access_token: ""
    });
  }

  function closeForm() {
    if (saving) {
      return;
    }

    setFormMode("closed");
    setFormData(emptyFormData);
  }

  function handleInputChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value
    }));
  }

  function handleClearField(fieldName) {
    setFormData((previous) => ({
      ...previous,
      [fieldName]: ""
    }));
  }

  function handleSearchSubmit(event) {
    event.preventDefault();
    setAppliedSearchValue(searchValue.trim());
  }

  function handleClearSearch() {
    setSearchValue("");
    setAppliedSearchValue("");
  }

  async function handleCopyAuthUrl(url) {
    if (!url) {
      showToast("Enter API key and redirect URL first.", "warning");
      return;
    }

    try {
      await navigator.clipboard.writeText(url);
      showToast("Upstox login URL copied.", "success");
    } catch {
      showToast("Unable to copy login URL.", "error");
    }
  }

  async function handleSave() {
    if (!formBroker) {
      showToast("Select a provider before saving connection.", "warning");
      return;
    }

    if (!formBroker.apiSupported) {
      showToast(`${formBroker.name} backend APIs are not added yet.`, "warning");
      return;
    }

    if (!isAdminControlAllowed) {
      showToast("Admin access required to save connections.", "error");
      return;
    }

    const hasAuthorizationCode = formData.authorization_code.trim();
    const hasAccessToken = formData.access_token.trim();

    if (!hasAuthorizationCode && !hasAccessToken) {
      showToast(
        "Enter authorization code or paste access token before saving.",
        "warning"
      );
      return;
    }

    if (
      hasAuthorizationCode &&
      (!formData.api_key.trim() ||
        !formData.api_secret.trim() ||
        !formData.redirect_url.trim())
    ) {
      showToast(
        "API key, API secret, and redirect URL are required with authorization code.",
        "warning"
      );
      return;
    }

    setSaving(true);

    try {
      if (formBroker.id === "upstox") {
        await saveUpstoxConnection({
          api_key: formData.api_key.trim(),
          api_secret: formData.api_secret.trim(),
          redirect_url: formData.redirect_url.trim(),
          authorization_code: formData.authorization_code.trim(),
          access_token: formData.access_token.trim()
        });
      }

      showToast(`${formBroker.name} connection saved successfully.`, "success");
      await loadConnections(false);
      setFormMode("closed");
      setFormData(emptyFormData);
    } catch (error) {
      showToast(
        getErrorMessage(error, `Unable to save ${formBroker.name} connection.`),
        "error"
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleTest(provider) {
    const broker = brokers.find((item) => item.id === provider);

    if (!broker) {
      showToast("Select a provider before testing connection.", "warning");
      return;
    }

    if (!broker.apiSupported) {
      showToast(`${broker.name} backend APIs are not added yet.`, "warning");
      return;
    }

    if (!isAdminControlAllowed) {
      showToast("Admin access required to test connections.", "error");
      return;
    }

    setTestingProvider(provider);

    try {
      let response = null;

      if (broker.id === "upstox") {
        response = await testUpstoxConnection();
      }

      showToast(
        response?.data?.message ||
          `${broker.name} connection tested successfully.`,
        response?.data?.status === "limited" ? "warning" : "success"
      );
      await loadConnections(false);
    } catch (error) {
      showToast(
        getErrorMessage(error, `Unable to test ${broker.name} connection.`),
        "error"
      );
    } finally {
      setTestingProvider("");
    }
  }

  async function handleDisconnect(provider) {
    const broker = brokers.find((item) => item.id === provider);

    if (!broker) {
      showToast("Select a provider before deleting connection.", "warning");
      return;
    }

    if (!broker.apiSupported) {
      showToast(`${broker.name} backend APIs are not added yet.`, "warning");
      return;
    }

    if (!isAdminControlAllowed) {
      showToast("Admin access required to delete connections.", "error");
      return;
    }

    setDisconnectingProvider(provider);

    try {
      if (broker.id === "upstox") {
        await disconnectUpstoxConnection();
      }

      setConnections((previous) =>
        previous.filter((item) => item.provider !== provider)
      );

      if (formData.provider === provider) {
        setFormMode("closed");
        setFormData(emptyFormData);
      }

      showToast(`${broker.name} connection deleted successfully.`, "success");
    } catch (error) {
      showToast(
        getErrorMessage(error, `Unable to delete ${broker.name}.`),
        "error"
      );
    } finally {
      setDisconnectingProvider("");
    }
  }

  function renderCell(row, column) {
    if (column.key === "provider") {
      return (
        <span className="truncate oa-code-font font-semibold text-white">
          {row.provider}
        </span>
      );
    }

    if (column.key === "status") {
      return <StatusBadge status={row.status} />;
    }

    if (column.key === "updated_at") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatDateTime(row.updated_at)}
        </span>
      );
    }

    if (column.key === "token_expiry") {
      return (
        <span className="truncate oa-code-font text-white">
          {row.token_expiry}
        </span>
      );
    }

    if (column.key === "updated_by") {
      return (
        <span className="truncate oa-code-font text-oa-muted">
          {row.updated_by}
        </span>
      );
    }

    return <span className="truncate">--</span>;
  }

  function renderActions(row) {
    const hasConnection = Boolean(row.connection);
    const isTesting = testingProvider === row.broker.id;
    const isDeleting = disconnectingProvider === row.broker.id;

    return (
      <div className="flex justify-end gap-2">
        <IconButton
          icon={Edit3}
          label="Edit connection"
          variant="default"
          disabled={
            !hasConnection || !row.broker.apiSupported || !isAdminControlAllowed
          }
          onClick={() => openEditForm(row.broker.id)}
          tooltipSide="left"
        />

        <button
          type="button"
          disabled={
            isTesting ||
            !hasConnection ||
            !row.broker.apiSupported ||
            !isAdminControlAllowed
          }
          onClick={() => handleTest(row.broker.id)}
          className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-oa-muted outline-none transition hover:bg-oa-card hover:text-white focus:border-oa-muted disabled:cursor-not-allowed disabled:opacity-60"
          aria-label={isTesting ? "Testing connection" : "Test connection"}
          title={isTesting ? "Testing connection" : "Test connection"}
        >
          {isTesting ? (
            <Spinner size="xs" color="light" />
          ) : (
            <PlugZap size={15} />
          )}
        </button>

        <button
          type="button"
          disabled={
            isDeleting ||
            !hasConnection ||
            !row.broker.apiSupported ||
            !isAdminControlAllowed
          }
          onClick={() => handleDisconnect(row.broker.id)}
          className="flex h-8 w-8 items-center justify-center rounded border border-red-500/30 bg-red-950/20 text-red-300 outline-none transition hover:border-red-500/60 hover:bg-red-950/40 hover:text-red-200 focus:border-red-500 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label={isDeleting ? "Deleting connection" : "Delete connection"}
          title={isDeleting ? "Deleting connection" : "Delete connection"}
        >
          {isDeleting ? (
            <Spinner size="xs" color="light" />
          ) : (
            <Trash2 size={15} />
          )}
        </button>
      </div>
    );
  }

  return (
    <MainLayout>
      <section className="min-h-screen bg-black p-3">
        <div className="space-y-3">
          {!isAdminControlAllowed && (
            <div className="flex gap-3 rounded border border-red-500/30 bg-red-950/20 p-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-red-500/40 bg-black text-red-300">
                <AlertTriangle size={18} />
              </div>

              <div>
                <p className={oaCardStyles.headerTitle}>
                  Admin access required
                </p>
                <p className={`mt-1 ${oaFormTextStyles.helper}`}>
                  Only admin and super admin users can save, test, edit, or
                  delete provider connections.
                </p>
              </div>
            </div>
          )}

          <div className={oaCardStyles.wrapper}>
            <div className={oaCardStyles.header}>
              <h2 className={oaCardStyles.headerTitle}>Connections</h2>
            </div>

            <div className="relative z-30 border-b border-oa-border bg-black px-3 py-1.5">
              <form
                onSubmit={handleSearchSubmit}
                className="flex flex-wrap items-center gap-2"
              >
                <div className="relative w-full md:w-80">
                  <Input
                    value={searchValue}
                    onChange={(event) => setSearchValue(event.target.value)}
                    placeholder="Search connections"
                    className="pr-9"
                  />

                  {searchValue ? (
                    <button
                      type="button"
                      onClick={handleClearSearch}
                      className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-oa-muted transition hover:bg-oa-card hover:text-white"
                      aria-label="Clear search"
                    >
                      <X size={13} />
                    </button>
                  ) : null}
                </div>

                <button
                  type="submit"
                  className="flex h-8 w-8 items-center justify-center rounded border border-sky-500/30 bg-sky-950/20 text-sky-300 outline-none transition hover:border-sky-500/60 hover:bg-sky-950/40 hover:text-sky-200 focus:border-sky-500"
                  aria-label="Search connections"
                  title="Search connections"
                >
                  <Search size={14} />
                </button>

                <IconButton
                  icon={Plus}
                  label="Add connection"
                  variant="default"
                  disabled={!isAdminControlAllowed}
                  onClick={openAddForm}
                  tooltipSide="top"
                />

                <IconButton
                  icon={RefreshCcw}
                  label="Refresh"
                  variant="refresh"
                  disabled={loading}
                  onClick={() => loadConnections(true)}
                  tooltipSide="top"
                />
              </form>
            </div>

            <div className="bg-black [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
              <DataTable
                columns={connectionColumns}
                rows={filteredRows}
                loading={loading}
                loadingMessage="Loading connections"
                emptyMessage="No provider connections found."
                gridTemplateColumns={connectionGridTemplateColumns}
                minWidth="min-w-full"
                getRowKey={(row) => row.id}
                renderCell={renderCell}
                renderActions={renderActions}
              />
            </div>
          </div>
        </div>

        <ConnectionFormModal
          open={formOpen}
          mode={formMode}
          formData={formData}
          selectedConnection={selectedConnection}
          saving={saving}
          isAdminControlAllowed={isAdminControlAllowed}
          onClose={closeForm}
          onSave={handleSave}
          onInputChange={handleInputChange}
          onClearField={handleClearField}
          onCopyAuthUrl={handleCopyAuthUrl}
        />
      </section>
    </MainLayout>
  );
}

export default Connections;