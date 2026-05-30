import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Building2,
  CheckCircle2,
  Edit3,
  Info,
  PlugZap,
  RefreshCcw,
  Save,
  Trash2
} from "lucide-react";

import MainLayout from "../../components/layout/MainLayout";
import Spinner from "../../components/common/Spinner";
import IconButton from "../../components/common/IconButton";
import Input from "../../components/common/Input";
import Tooltip from "../../components/common/Tooltip";
import { useToast } from "../../components/common/ToastProvider";
import {
  oaCardStyles,
  oaFormTextStyles,
  oaTableStyles,
  oaTabStyles
} from "../../components/common/uiStyles";
import {
  disconnectUpstoxConnection,
  getConnections,
  saveUpstoxConnection,
  testUpstoxConnection
} from "../../api/connectionApi";

const emptyFormData = {
  api_key: "",
  api_secret: "",
  redirect_url: "",
  access_token: ""
};

const brokers = [
  {
    id: "upstox",
    name: "Upstox",
    description: "Token based broker connection.",
    apiSupported: true
  }
];

const sectionHeaderClass = "border-b border-oa-border bg-zinc-900/80 px-4 py-3";

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

  if (status === "failed") {
    return "Failed";
  }

  if (status === "saved") {
    return "Saved";
  }

  return "Not Connected";
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

function InfoRow({ label, value, children }) {
  return (
    <div className="grid grid-cols-[130px_1fr] items-center gap-3 border-b border-oa-border/70 py-2.5 last:border-b-0">
      <span className={oaFormTextStyles.label}>{label}</span>
      <span className={`min-w-0 truncate text-right ${oaFormTextStyles.value}`}>
        {children || value}
      </span>
    </div>
  );
}

function Connections() {
  const [connections, setConnections] = useState([]);
  const [selectedBrokerId, setSelectedBrokerId] = useState("upstox");
  const [formData, setFormData] = useState(emptyFormData);
  const [editing, setEditing] = useState(false);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);

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

  const selectedBroker = useMemo(() => {
    return brokers.find((item) => item.id === selectedBrokerId) || null;
  }, [selectedBrokerId]);

  const selectedConnection = selectedBroker
    ? connectionsByProvider[selectedBroker.id] || null
    : null;

  const selectedStatus = getConnectionStatus(selectedConnection);
  const isSelectedConnected = selectedStatus === "connected";
  const hasSelectedBroker = Boolean(selectedBroker);
  const isSelectedBrokerSupported = Boolean(selectedBroker?.apiSupported);

  const controlsDisabled =
    !isAdminControlAllowed ||
    !hasSelectedBroker ||
    !isSelectedBrokerSupported ||
    (!editing && Boolean(selectedConnection));

  async function loadConnections(showRefreshToast = false) {
    setLoading(true);

    try {
      const response = await getConnections();
      setConnections(response.data.connections || []);

      if (showRefreshToast) {
        showToast("Connections refreshed successfully.", "success");
      }
    } catch (error) {
      showToast(
        error.response?.data?.detail || "Unable to load connections.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadConnections(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedBroker) {
      setFormData(emptyFormData);
      setEditing(false);
      return;
    }

    if (selectedConnection) {
      setFormData({
        api_key: selectedConnection.api_key || "",
        api_secret: "",
        redirect_url: selectedConnection.redirect_url || "",
        access_token: ""
      });
      setEditing(false);
      return;
    }

    setFormData(emptyFormData);
    setEditing(true);
  }, [selectedBroker, selectedConnection]);

  function handleBrokerSelect(brokerId) {
    setSelectedBrokerId(brokerId);
  }

  function handleInputChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value
    }));
  }

  async function handleSave(event) {
    event.preventDefault();

    if (!selectedBroker) {
      showToast("Select a broker before saving token.", "warning");
      return;
    }

    if (!isSelectedBrokerSupported) {
      showToast(
        `${selectedBroker.name} backend APIs are not added yet.`,
        "warning"
      );
      return;
    }

    if (!isAdminControlAllowed) {
      showToast("Admin access required to save connections.", "error");
      return;
    }

    setSaving(true);

    try {
      if (selectedBroker.id === "upstox") {
        await saveUpstoxConnection({
          api_key: formData.api_key || "",
          api_secret: formData.api_secret || "",
          redirect_url: formData.redirect_url || "",
          access_token: formData.access_token
        });
      }

      showToast(`${selectedBroker.name} token saved successfully.`, "success");
      await loadConnections(false);

      setFormData((previous) => ({
        ...previous,
        access_token: ""
      }));
      setEditing(false);
    } catch (error) {
      showToast(
        error.response?.data?.detail ||
          `Unable to save ${selectedBroker.name} token.`,
        "error"
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    if (!selectedBroker) {
      showToast("Select a broker before testing connection.", "warning");
      return;
    }

    if (!isSelectedBrokerSupported) {
      showToast(
        `${selectedBroker.name} backend APIs are not added yet.`,
        "warning"
      );
      return;
    }

    if (!isAdminControlAllowed) {
      showToast("Admin access required to test connections.", "error");
      return;
    }

    setTesting(true);

    try {
      let response = null;

      if (selectedBroker.id === "upstox") {
        response = await testUpstoxConnection();
      }

      showToast(
        response?.data?.message ||
          `${selectedBroker.name} connection tested successfully.`,
        "success"
      );
      await loadConnections(false);
    } catch (error) {
      showToast(
        error.response?.data?.detail ||
          `Unable to test ${selectedBroker.name} connection.`,
        "error"
      );
    } finally {
      setTesting(false);
    }
  }

  async function handleDisconnect() {
    if (!selectedBroker) {
      showToast("Select a broker before disconnecting.", "warning");
      return;
    }

    if (!isSelectedBrokerSupported) {
      showToast(
        `${selectedBroker.name} backend APIs are not added yet.`,
        "warning"
      );
      return;
    }

    if (!isAdminControlAllowed) {
      showToast("Admin access required to disconnect connections.", "error");
      return;
    }

    setDisconnecting(true);

    try {
      if (selectedBroker.id === "upstox") {
        await disconnectUpstoxConnection();
      }

      setConnections((previous) =>
        previous.filter((item) => item.provider !== selectedBroker.id)
      );
      setFormData(emptyFormData);
      setEditing(true);
      showToast(`${selectedBroker.name} disconnected successfully.`, "success");
    } catch (error) {
      showToast(
        error.response?.data?.detail ||
          `Unable to disconnect ${selectedBroker.name}.`,
        "error"
      );
    } finally {
      setDisconnecting(false);
    }
  }

  return (
    <MainLayout>
      <section className="min-h-screen bg-black p-3">
        <div className="space-y-3">
          <div className={oaCardStyles.wrapper}>
            <div className={oaCardStyles.header}>
              <h2 className={oaCardStyles.headerTitle}>Connections</h2>
              <p className={oaCardStyles.headerSubtitle}>
                Admin controlled external broker and market data provider
                credentials.
              </p>
            </div>

            <div className="flex flex-col gap-2 border-b border-oa-border bg-black px-3 py-1.5 md:flex-row md:items-center md:justify-between">
              <div className={oaTabStyles.wrapper}>
                {brokers.map((broker) => {
                  const isActive = selectedBrokerId === broker.id;

                  return (
                    <button
                      key={broker.id}
                      type="button"
                      onClick={() => handleBrokerSelect(broker.id)}
                      className={`${oaTabStyles.button} ${
                        isActive ? oaTabStyles.active : oaTabStyles.inactive
                      }`}
                    >
                      {broker.name}
                    </button>
                  );
                })}
              </div>

              <div className="flex items-center gap-2">
                <IconButton
                  icon={RefreshCcw}
                  label="Refresh"
                  variant="refresh"
                  disabled={loading}
                  onClick={() => loadConnections(true)}
                  tooltipSide="top"
                />
              </div>
            </div>

            {!isAdminControlAllowed && (
              <div className="border-b border-oa-border bg-black p-3">
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
                      disconnect provider connections.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="grid min-h-[360px] gap-0 bg-black xl:grid-cols-[minmax(420px,1fr)_360px]">
              <div className="border-b border-oa-border xl:border-b-0 xl:border-r">
                <div className={sectionHeaderClass}>
                  <h3 className={oaCardStyles.headerTitle}>
                    Connection Setup
                  </h3>
                  <p className={oaCardStyles.headerSubtitle}>
                    {selectedBroker
                      ? selectedBroker.description
                      : "Select a broker from the top row."}
                  </p>
                </div>

                {!selectedBroker ? (
                  <div className="flex min-h-[260px] items-center justify-center p-4">
                    <div className="max-w-sm text-center oa-table-font">
                      <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded border border-oa-border bg-oa-panel text-oa-muted">
                        <Building2 size={18} />
                      </div>
                      <p className={oaCardStyles.headerTitle}>
                        No broker selected
                      </p>
                      <p className={`mt-1 leading-5 ${oaFormTextStyles.helper}`}>
                        Select a broker from the top row to open token
                        connection controls.
                      </p>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleSave} className="p-3 oa-table-font">
                    {!selectedBroker.apiSupported && (
                      <div className="mb-3 flex gap-3 rounded border border-amber-500/30 bg-amber-950/20 p-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-amber-500/40 bg-black text-amber-300">
                          <Info size={18} />
                        </div>

                        <div>
                          <p className={oaCardStyles.headerTitle}>
                            Backend API not added yet
                          </p>
                          <p className={`mt-1 ${oaFormTextStyles.helper}`}>
                            {selectedBroker.name} is visible in the broker
                            list, but save, test, and disconnect will work
                            after adding backend API support.
                          </p>
                        </div>
                      </div>
                    )}

                    <div className="grid gap-2">
                      <Input
                        name="access_token"
                        type="password"
                        value={formData.access_token}
                        onChange={handleInputChange}
                        placeholder={
                          selectedConnection?.has_access_token
                            ? "Token saved - enter only to replace"
                            : `${selectedBroker.name} Access Token`
                        }
                        required={!selectedConnection?.has_access_token}
                        disabled={controlsDisabled}
                      />
                    </div>

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                      <p className={oaFormTextStyles.helper}>
                        {selectedConnection && !editing
                          ? "Click edit to replace saved token."
                          : "Only admin and super admin users can manage this connection."}
                      </p>

                      <div className="flex items-center gap-2">
                        <Tooltip text="Edit token" side="top">
                          <button
                            type="button"
                            disabled={
                              !selectedConnection ||
                              !selectedBroker.apiSupported ||
                              !isAdminControlAllowed
                            }
                            onClick={() => setEditing(true)}
                            className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-amber-300 outline-none transition hover:border-amber-500/60 hover:bg-amber-950/40 hover:text-amber-200 focus:border-amber-500 disabled:cursor-not-allowed disabled:opacity-60"
                            aria-label="Edit token"
                          >
                            <Edit3 size={15} />
                          </button>
                        </Tooltip>

                        <Tooltip text="Save token" side="top">
                          <button
                            type="submit"
                            disabled={saving || controlsDisabled}
                            className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                            aria-label="Save token"
                          >
                            {saving ? (
                              <Spinner size="xs" color="light" />
                            ) : (
                              <Save size={15} />
                            )}
                          </button>
                        </Tooltip>

                        <Tooltip text="Test connection" side="top">
                          <button
                            type="button"
                            disabled={
                              testing ||
                              !selectedConnection ||
                              !selectedBroker.apiSupported ||
                              !isAdminControlAllowed
                            }
                            onClick={handleTest}
                            className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-sky-300 outline-none transition hover:border-sky-500/60 hover:bg-sky-950/40 hover:text-sky-200 focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
                            aria-label="Test connection"
                          >
                            {testing ? (
                              <Spinner size="xs" color="light" />
                            ) : (
                              <PlugZap size={15} />
                            )}
                          </button>
                        </Tooltip>

                        <IconButton
                          icon={Trash2}
                          label="Disconnect"
                          variant="danger"
                          tooltipSide="top"
                          disabled={
                            !selectedConnection ||
                            disconnecting ||
                            !selectedBroker.apiSupported ||
                            !isAdminControlAllowed
                          }
                          onClick={handleDisconnect}
                        />
                      </div>
                    </div>
                  </form>
                )}
              </div>

              <div>
                <div className={sectionHeaderClass}>
                  <h3 className={oaCardStyles.headerTitle}>
                    Connection Information
                  </h3>
                  <p className={oaCardStyles.headerSubtitle}>
                    Selected broker token details.
                  </p>
                </div>

                {loading ? (
                  <div
                    className={`flex min-h-[260px] items-center justify-center gap-2 px-3 py-8 oa-table-font ${oaTableStyles.mutedText}`}
                  >
                    <Spinner size="sm" color="light" />
                    Loading connections
                  </div>
                ) : !selectedBroker ? (
                  <div className="flex min-h-[260px] items-center justify-center p-4">
                    <div className="max-w-sm text-center oa-table-font">
                      <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded border border-oa-border bg-oa-panel text-oa-muted">
                        <Activity size={18} />
                      </div>
                      <p className={oaCardStyles.headerTitle}>
                        No broker selected
                      </p>
                      <p className={`mt-1 leading-5 ${oaFormTextStyles.helper}`}>
                        Select a broker to view its token information.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="px-3 py-2 oa-table-font">
                    <InfoRow label="Broker Name" value={selectedBroker.name} />

                    <InfoRow label="Connection Status">
                      <span
                        className={`inline-flex items-center justify-end gap-1.5 ${
                          isSelectedConnected
                            ? "text-emerald-200"
                            : "text-white"
                        }`}
                      >
                        {isSelectedConnected && <CheckCircle2 size={13} />}
                        {selectedBroker.apiSupported
                          ? getStatusLabel(selectedStatus)
                          : "Not Configured"}
                      </span>
                    </InfoRow>

                    <InfoRow
                      label="Updated At"
                      value={formatDateTime(getLastUpdated(selectedConnection))}
                    />

                    <InfoRow
                      label="Token Expiry"
                      value={getTokenExpiry(selectedConnection)}
                    />

                    <InfoRow
                      label="Updated By"
                      value={
                        selectedConnection ? formatUserName(currentUser) : "--"
                      }
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>
    </MainLayout>
  );
}

export default Connections;