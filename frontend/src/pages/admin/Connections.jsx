import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Check,
  Edit3,
  ExternalLink,
  KeyRound,
  Plus,
  PlugZap,
  RefreshCcw,
  Send,
  Trash2,
  X
} from "lucide-react";

import MainLayout from "../../components/layout/MainLayout";
import Spinner from "../../components/common/Spinner";
import IconButton from "../../components/common/IconButton";
import Tooltip from "../../components/common/Tooltip";
import Input from "../../components/common/Input";
import Select from "../../components/common/Select";
import Modal from "../../components/common/Modal";
import DataTable from "../../components/tables/DataTable";
import TableToolbar from "../../components/tables/TableToolbar";
import { useToast } from "../../components/common/ToastProvider";
import {
  oaCardStyles,
  oaFormTextStyles,
  oaPillStyles
} from "../../components/common/uiStyles";
import {
  disconnectTelegramConnection,
  disconnectUpstoxConnection,
  getConnections,
  getUpstoxAuthorizeUrl,
  saveTelegramConnection,
  saveUpstoxConnection,
  testTelegramConnection,
  testUpstoxConnection
} from "../../api/connectionApi";

const UPSTOX_REDIRECT_URL = import.meta.env.VITE_UPSTOX_REDIRECT_URL || "http://localhost:5173/connections/upstox/callback";

const emptyFormData = {
  provider: "",
  api_key: "",
  api_secret: "",
  redirect_url: "",
  analytical_token: "",
  access_token: "",
  bot_token: ""
};

const brokers = [
  {
    id: "upstox",
    name: "Upstox",
    description: "Broker connection.",
    apiSupported: true,
    icon: PlugZap
  },
  {
    id: "telegram",
    name: "Telegram",
    description: "Bot alert connection.",
    apiSupported: true,
    icon: Send
  }
];

const providerOptions = [
  {
    value: "",
    label: "Select provider"
  },
  ...brokers.map((broker) => ({
    value: broker.id,
    label: broker.name
  }))
];

const providerFilterOptions = [
  { value: "all", label: "All Providers" },
  ...brokers.map((broker) => ({
    value: broker.id,
    label: broker.name
  }))
];

const statusFilterOptions = [
  { value: "all", label: "All Status" },
  { value: "connected", label: "Connected" },
  { value: "limited", label: "Limited" },
  { value: "failed", label: "Failed" },
  { value: "saved", label: "Saved" },
  { value: "not_connected", label: "Not Connected" }
];

const connectionColumns = [
  { key: "provider", label: "Provider" },
  { key: "status", label: "Status" },
  { key: "updated_at", label: "Updated At" },
  { key: "token_expiry", label: "Token Expiry" },
  { key: "updated_by", label: "Updated By" }
];

const connectionGridTemplateColumns = "1.4fr 0.9fr 1.1fr 1.1fr 1.1fr 168px";

function normalizeCellValue(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }

  return String(value);
}

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

function getResponseToastType(status) {
  if (status === "limited") {
    return "warning";
  }

  if (status === "failed" || status === "invalid" || status === "error") {
    return "error";
  }

  return "success";
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

function getLastUpdated(connection) {
  return (
    connection?.updated_at ||
    connection?.last_updated_at ||
    connection?.last_tested_at ||
    connection?.created_at ||
    ""
  );
}

function getTokenExpiry(connection, provider) {
  if (!connection) {
    return "--";
  }

  if (provider === "telegram") {
    return "Bot token";
  }

  const explicitExpiry =
    connection?.access_token_expires_at ||
    connection?.token_expires_at ||
    connection?.expires_at;

  if (explicitExpiry) {
    return formatDateTime(explicitExpiry);
  }

  if (connection?.has_access_token) {
    return "Expiry calculating";
  }

  return "--";
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
  if (key === "status") {
    return getStatusLabel(row.status);
  }

  if (key === "updated_at") {
    return formatDateTime(row.updated_at);
  }

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

function StatusBadge({ status }) {
  return (
    <span className={`${oaPillStyles.base} ${getStatusClass(status)}`}>
      {getStatusLabel(status)}
    </span>
  );
}

function ClearInputButton({ label, onClick }) {
  return (
    <Tooltip text={label} side="top">
      <button
        type="button"
        onClick={onClick}
        className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-oa-muted transition hover:bg-oa-card hover:text-white"
        aria-label={label}
      >
        <X size={13} />
      </button>
    </Tooltip>
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
  onUseDefaultRedirectUrl
}) {
  const selectedBroker =
    brokers.find((broker) => broker.id === formData.provider) || null;

  const isUpstox = formData.provider === "upstox";
  const isTelegram = formData.provider === "telegram";
  const hasProviderSelected = Boolean(selectedBroker);

  const title = mode === "edit" ? "Edit Connection" : "Add Connection";

  function handleSubmit(event) {
    event.preventDefault();
    onSave();
  }

  return (
    <Modal
      open={open}
      title={title}
      subtitle=""
      onClose={onClose}
      width="max-w-xl"
      footer={
        <div className="flex items-center justify-end gap-2">
          <IconButton
            icon={X}
            label="Cancel"
            variant="filterCancel"
            size="filter"
            disabled={saving}
            onClick={onClose}
            tooltipSide="top"
          />

          <IconButton
            icon={Check}
            label={mode === "edit" ? "Update connection" : "Save connection"}
            variant="filterApply"
            size="filter"
            disabled={saving || !isAdminControlAllowed || !hasProviderSelected}
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

        {isUpstox ? (
          <div className="space-y-3">
            <div>
              <label className={oaFormTextStyles.label}>API Key</label>
              <div className="relative mt-1">
                <Input
                  name="api_key"
                  value={formData.api_key}
                  onChange={onInputChange}
                  placeholder={
                    selectedConnection?.api_key
                      ? "Saved - enter to replace"
                      : "Enter Upstox API key"
                  }
                  className="pr-9"
                  autoFocus
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

            <div>
              <div className="flex items-center justify-between gap-2">
                <label className={oaFormTextStyles.label}>Redirect URL</label>

                <Tooltip text="Use app redirect URL" side="top">
                  <button
                    type="button"
                    onClick={onUseDefaultRedirectUrl}
                    className="inline-flex items-center gap-1 rounded-sm border border-oa-border bg-black px-2 py-1 text-[11px] text-sky-300 transition hover:border-sky-500/50 hover:bg-sky-950/30 hover:text-sky-200"
                    aria-label="Use app redirect URL"
                  >
                    <ExternalLink size={12} />
                    Use app URL
                  </button>
                </Tooltip>
              </div>

              <div className="relative mt-1">
                <Input
                  name="redirect_url"
                  value={formData.redirect_url}
                  onChange={onInputChange}
                  placeholder="Enter Upstox redirect URL"
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

            <div>
              <label className={oaFormTextStyles.label}>
                Analytical Token
              </label>
              <div className="relative mt-1">
                <Input
                  name="analytical_token"
                  type="password"
                  value={formData.analytical_token}
                  onChange={onInputChange}
                  placeholder={
                    selectedConnection?.has_analytical_token
                      ? "Saved - enter to replace"
                      : "Enter analytical token"
                  }
                  className="pr-9"
                />

                {formData.analytical_token ? (
                  <ClearInputButton
                    label="Clear analytical token"
                    onClick={() => onClearField("analytical_token")}
                  />
                ) : null}
              </div>
            </div>

            <div>
              <label className={oaFormTextStyles.label}>
                Manual Access Token
              </label>
              <div className="relative mt-1">
                <Input
                  name="access_token"
                  type="password"
                  value={formData.access_token}
                  onChange={onInputChange}
                  placeholder={
                    selectedConnection?.has_access_token
                      ? "Saved - enter to replace"
                      : "Paste access token"
                  }
                  className="pr-9"
                />

                {formData.access_token ? (
                  <ClearInputButton
                    label="Clear manual access token"
                    onClick={() => onClearField("access_token")}
                  />
                ) : null}
              </div>
            </div>
          </div>
        ) : null}

        {isTelegram ? (
          <div>
            <label className={oaFormTextStyles.label}>Bot Token</label>
            <div className="relative mt-1">
              <Input
                name="bot_token"
                type="password"
                value={formData.bot_token}
                onChange={onInputChange}
                placeholder={
                  selectedConnection?.has_access_token
                    ? "Saved - enter to replace"
                    : "Enter Telegram bot token"
                }
                className="pr-9"
                autoFocus
              />

              {formData.bot_token ? (
                <ClearInputButton
                  label="Clear bot token"
                  onClick={() => onClearField("bot_token")}
                />
              ) : null}
            </div>
          </div>
        ) : null}

        <button type="submit" className="hidden" aria-hidden="true">
          Submit {selectedBroker?.name || "connection"}
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
  const [providerFilter, setProviderFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const [columnFilters, setColumnFilters] = useState({});
  const [draftColumnFilters, setDraftColumnFilters] = useState({});
  const [activeFilter, setActiveFilter] = useState(null);

  const [sortConfig, setSortConfig] = useState({
    key: null,
    direction: null
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testingProvider, setTestingProvider] = useState("");
  const [disconnectingProvider, setDisconnectingProvider] = useState("");
  const [authorizingProvider, setAuthorizingProvider] = useState("");

  const { showToast } = useToast();

  const currentUser = useMemo(() => getStoredCurrentUser(), []);
  const isAdminControlAllowed = ["admin", "super_admin"].includes(
    currentUser?.role
  );

  const connectionsByProvider = useMemo(() => {
    return connections.reduce((accumulator, item) => {
      if (item?.provider) {
        accumulator[item.provider] = item;
      }

      return accumulator;
    }, {});
  }, [connections]);

  const rows = useMemo(() => {
    return brokers
      .map((broker) => {
        const connection = connectionsByProvider[broker.id] || null;

        return {
          id: broker.id,
          broker,
          connection,
          provider: broker.name,
          provider_id: broker.id,
          description: broker.description,
          status: getConnectionStatus(connection),
          updated_at: getLastUpdated(connection),
          token_expiry: getTokenExpiry(connection, broker.id),
          updated_by: formatUserName(currentUser)
        };
      })
      .filter(Boolean);
  }, [connectionsByProvider, currentUser]);

  const headerValues = useMemo(() => {
    return connectionColumns.reduce((result, column) => {
      result[column.key] = getFilterValues(rows, column.key);
      return result;
    }, {});
  }, [rows]);

  const filteredRows = useMemo(() => {
    let result = rows;

    const query = appliedSearchValue.trim().toLowerCase();

    if (query) {
      result = result.filter((row) => {
        const values = [
          row.provider,
          row.description,
          getStatusLabel(row.status),
          formatDateTime(row.updated_at),
          row.token_expiry,
          row.updated_by
        ];

        return values.some((value) =>
          String(value).toLowerCase().includes(query)
        );
      });
    }

    if (providerFilter !== "all") {
      result = result.filter((row) => row.provider_id === providerFilter);
    }

    if (statusFilter !== "all") {
      result = result.filter((row) => row.status === statusFilter);
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
    rows,
    appliedSearchValue,
    providerFilter,
    statusFilter,
    columnFilters,
    sortConfig
  ]);

  const formBroker = useMemo(() => {
    return brokers.find((item) => item.id === formData.provider) || null;
  }, [formData.provider]);

  const selectedConnection = formData.provider
    ? connectionsByProvider[formData.provider] || null
    : null;

  const formOpen = formMode !== "closed";

  function hasAnyActiveFilter() {
    return (
      appliedSearchValue.trim() !== "" ||
      providerFilter !== "all" ||
      statusFilter !== "all" ||
      sortConfig.key !== null ||
      Object.values(columnFilters).some(
        (value) => Array.isArray(value) && value.length > 0
      )
    );
  }

  function clearAllFilters() {
    setSearchValue("");
    setAppliedSearchValue("");
    setProviderFilter("all");
    setStatusFilter("all");
    setColumnFilters({});
    setDraftColumnFilters({});
    setSortConfig({
      key: null,
      direction: null
    });
    setActiveFilter(null);
  }

  function clearSearchFilter() {
    setSearchValue("");
    setAppliedSearchValue("");
  }

  function clearProviderFilter() {
    setProviderFilter("all");
  }

  function clearStatusFilter() {
    setStatusFilter("all");
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
      ...emptyFormData,
      provider,
      api_key: connection?.api_key || "",
      redirect_url: connection?.redirect_url || ""
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

    if (name === "provider") {
      setFormData({
        ...emptyFormData,
        provider: value
      });
      return;
    }

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

  function handleUseDefaultRedirectUrl() {
    setFormData((previous) => ({
      ...previous,
      redirect_url: UPSTOX_REDIRECT_URL
    }));
  }

  function handleSearchSubmit(event) {
    event.preventDefault();
    setAppliedSearchValue(searchValue.trim());
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

    const apiKey = formData.api_key.trim();
    const apiSecret = formData.api_secret.trim();
    const redirectUrl = formData.redirect_url.trim();

    const analyticalToken = formData.analytical_token.trim();
    const accessToken = formData.access_token.trim();

    if (formBroker.id === "upstox") {
      const hasStoredApiSecret =
        Boolean(selectedConnection?.has_api_secret);

      const effectiveApiSecret =
        apiSecret || (hasStoredApiSecret ? "__saved__" : "");

      const hasAnyValue =
        apiKey ||
        effectiveApiSecret ||
        redirectUrl ||
        analyticalToken ||
        accessToken;

      const hasPartialApiCredential =
        apiKey ||
        effectiveApiSecret ||
        redirectUrl;

      const hasCompleteApiCredential =
        apiKey &&
        effectiveApiSecret &&
        redirectUrl;

      if (!hasAnyValue) {
        showToast(
          "Enter Upstox API key, API secret, redirect URL, analytical token, or manual access token.",
          "warning"
        );
        return;
      }

      if (hasPartialApiCredential && !hasCompleteApiCredential) {
        showToast(
          "Upstox API key, API secret, and redirect URL are required together.",
          "warning"
        );
        return;
      }
    }

    if (formBroker.id === "telegram" && !formData.bot_token.trim()) {
      showToast("Telegram bot token is required.", "warning");
      return;
    }

    setSaving(true);

    try {
      let response = null;

      if (formBroker.id === "upstox") {
        response = await saveUpstoxConnection({
          api_key: apiKey || null,
          api_secret: apiSecret || null,
          redirect_url: redirectUrl || null,
          analytical_token: analyticalToken || null,
          access_token: accessToken || null
        });

        await loadConnections(false);

        try {
          response = await testUpstoxConnection();
        } catch (testError) {
          showToast(
            getErrorMessage(testError, "Upstox token saved, but verification failed."),
            "error"
          );
          await loadConnections(false);
          setFormMode("closed");
          setFormData(emptyFormData);
          return;
        }
      }

      if (formBroker.id === "telegram") {
        response = await saveTelegramConnection({
          bot_token: formData.bot_token.trim()
        });
      }

      await loadConnections(false);

      showToast(
        response?.data?.message ||
          `${formBroker.name} connection saved successfully.`,
        getResponseToastType(response?.data?.status)
      );

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

  async function handleGenerateUpstoxAccessToken() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to generate access token.", "error");
      return;
    }

    setAuthorizingProvider("upstox");

    try {
      const response = await getUpstoxAuthorizeUrl();
      const authorizeUrl = response.data?.authorize_url;

      if (!authorizeUrl) {
        showToast("Unable to get Upstox authorization URL.", "error");
        return;
      }

      window.location.href = authorizeUrl;
    } catch (error) {
      showToast(
        getErrorMessage(
          error,
          "Save Upstox API key, API secret, and redirect URL first."
        ),
        "error"
      );
    } finally {
      setAuthorizingProvider("");
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

      if (broker.id === "telegram") {
        response = await testTelegramConnection();
      }

      showToast(
        response?.data?.message ||
          `${broker.name} connection tested successfully.`,
        getResponseToastType(response?.data?.status)
      );
      await loadConnections(false);
    } catch (error) {
      showToast(
        getErrorMessage(error, `Unable to test ${broker.name} connection.`),
        "error"
      );
      await loadConnections(false);
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

      if (broker.id === "telegram") {
        await disconnectTelegramConnection();
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
    const isAuthorizing = authorizingProvider === row.broker.id;

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

        {row.broker.id === "upstox" ? (
          <Tooltip
            text={
              isAuthorizing ? "Generating access token" : "Generate access token"
            }
            side="left"
          >
            <button
              type="button"
              disabled={
                isAuthorizing ||
                !hasConnection ||
                !row.broker.apiSupported ||
                !isAdminControlAllowed
              }
              onClick={handleGenerateUpstoxAccessToken}
              className="flex h-8 w-8 items-center justify-center rounded border border-sky-500/30 bg-sky-950/20 text-sky-300 outline-none transition hover:border-sky-500/60 hover:bg-sky-950/40 hover:text-sky-200 focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
              aria-label={
                isAuthorizing
                  ? "Generating access token"
                  : "Generate access token"
              }
            >
              {isAuthorizing ? (
                <Spinner size="xs" color="light" />
              ) : (
                <KeyRound size={15} />
              )}
            </button>
          </Tooltip>
        ) : null}

        <Tooltip
          text={isTesting ? "Testing connection" : "Test connection"}
          side="left"
        >
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
          >
            {isTesting ? (
              <Spinner size="xs" color="light" />
            ) : (
              <PlugZap size={15} />
            )}
          </button>
        </Tooltip>

        <Tooltip
          text={isDeleting ? "Deleting connection" : "Delete connection"}
          side="left"
        >
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
          >
            {isDeleting ? (
              <Spinner size="xs" color="light" />
            ) : (
              <Trash2 size={15} />
            )}
          </button>
        </Tooltip>
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

            <div className="border-b border-oa-border bg-black px-3 py-1.5 [&>div]:mb-0">
              <TableToolbar
                searchValue={searchValue}
                onSearchChange={setSearchValue}
                onSearchClear={clearSearchFilter}
                onSearchSubmit={handleSearchSubmit}
                searchActive={appliedSearchValue.trim() !== ""}
                searchPlaceholder="Search connections"
                filters={[
                  {
                    value: providerFilter,
                    onChange: (event) => setProviderFilter(event.target.value),
                    options: providerFilterOptions,
                    onClear: clearProviderFilter,
                    showClear: providerFilter !== "all",
                    ariaLabel: "Provider filter",
                    minWidth: "w-40"
                  },
                  {
                    value: statusFilter,
                    onChange: (event) => setStatusFilter(event.target.value),
                    options: statusFilterOptions,
                    onClear: clearStatusFilter,
                    showClear: statusFilter !== "all",
                    ariaLabel: "Status filter",
                    minWidth: "w-40"
                  }
                ]}
                hasActiveFilter={hasAnyActiveFilter()}
                onClearAll={clearAllFilters}
                loading={loading}
                rightActions={[
                  {
                    icon: RefreshCcw,
                    label: "Refresh",
                    variant: "refresh",
                    disabled: loading,
                    onClick: () => loadConnections(true)
                  },
                  {
                    icon: Plus,
                    label: "Add connection",
                    variant: "add",
                    disabled: !isAdminControlAllowed,
                    onClick: openAddForm
                  }
                ]}
              />
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
                filterConfig={{
                  activeFilter,
                  headerValues,
                  columnFilters,
                  draftColumnFilters,
                  rightAlignedKeys: ["status", "updated_at", "token_expiry"],
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
          onUseDefaultRedirectUrl={handleUseDefaultRedirectUrl}
        />
      </section>
    </MainLayout>
  );
}

export default Connections;
