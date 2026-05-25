import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Link,
  PlugZap,
  RefreshCcw,
  Save,
  ShieldCheck,
  Trash2
} from "lucide-react";

import MainLayout from "../../components/layout/MainLayout";
import Spinner from "../../components/common/Spinner";
import IconButton from "../../components/common/IconButton";
import Input from "../../components/common/Input";
import Tooltip from "../../components/common/Tooltip";
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

function maskValue(value) {
  if (!value) {
    return "--";
  }

  if (value.length <= 8) {
    return "********";
  }

  return `${value.slice(0, 4)}********${value.slice(-4)}`;
}

function formatRoleLabel(role) {
  if (!role) {
    return "--";
  }

  return String(role)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function Connections() {
  const [connection, setConnection] = useState(null);
  const [formData, setFormData] = useState(emptyFormData);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [actionMessage, setActionMessage] = useState("");

  const currentUser = useMemo(() => getStoredCurrentUser(), []);
  const isAdminControlAllowed = ["admin", "super_admin"].includes(
    currentUser?.role
  );

  async function loadConnections() {
    setLoading(true);
    setActionMessage("");

    try {
      const response = await getConnections();
      const upstoxConnection =
        response.data.connections.find((item) => item.provider === "upstox") ||
        null;

      setConnection(upstoxConnection);

      if (upstoxConnection) {
        setFormData({
          api_key: upstoxConnection.api_key || "",
          api_secret: "",
          redirect_url: upstoxConnection.redirect_url || "",
          access_token: ""
        });
      }
    } catch (error) {
      setActionMessage(
        error.response?.data?.detail || "Unable to load connections."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadConnections();
  }, []);

  function handleInputChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value
    }));
  }

  async function handleSave(event) {
    event.preventDefault();

    if (!isAdminControlAllowed) {
      setActionMessage("Admin access required to save connections.");
      return;
    }

    setSaving(true);
    setActionMessage("");

    try {
      await saveUpstoxConnection(formData);
      setActionMessage("Upstox credentials saved successfully.");
      await loadConnections();

      setFormData((previous) => ({
        ...previous,
        api_secret: "",
        access_token: ""
      }));
    } catch (error) {
      setActionMessage(
        error.response?.data?.detail || "Unable to save Upstox credentials."
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    if (!isAdminControlAllowed) {
      setActionMessage("Admin access required to test connections.");
      return;
    }

    setTesting(true);
    setActionMessage("");

    try {
      const response = await testUpstoxConnection();
      setActionMessage(
        response.data.message || "Upstox connection tested successfully."
      );
      await loadConnections();
    } catch (error) {
      setActionMessage(
        error.response?.data?.detail || "Unable to test Upstox connection."
      );
    } finally {
      setTesting(false);
    }
  }

  async function handleDisconnect() {
    if (!isAdminControlAllowed) {
      setActionMessage("Admin access required to disconnect connections.");
      return;
    }

    setDisconnecting(true);
    setActionMessage("");

    try {
      await disconnectUpstoxConnection();
      setConnection(null);
      setFormData(emptyFormData);
      setActionMessage("Upstox disconnected successfully.");
    } catch (error) {
      setActionMessage(
        error.response?.data?.detail || "Unable to disconnect Upstox."
      );
    } finally {
      setDisconnecting(false);
    }
  }

  const isConnected = connection?.connection_status === "connected";
  const controlsDisabled = !isAdminControlAllowed;

  return (
    <MainLayout>
      <section className="p-3">
        <div className="rounded border border-oa-border bg-oa-card p-3">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
            <div>
              <h2 className="text-sm font-semibold">Connections</h2>
              <p className="text-[11px] text-oa-muted">
                Admin controlled external market data provider credentials.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${
                  isAdminControlAllowed
                    ? "border-emerald-500/40 bg-emerald-950/50 text-emerald-200"
                    : "border-red-500/40 bg-red-950/50 text-red-200"
                }`}
              >
                {formatRoleLabel(currentUser?.role)} Control
              </span>

              <IconButton
                icon={RefreshCcw}
                label="Refresh"
                variant="refresh"
                disabled={loading}
                onClick={loadConnections}
                tooltipSide="left"
              />
            </div>
          </div>

          {!isAdminControlAllowed && (
            <div className="mb-3 flex gap-3 rounded border border-red-500/30 bg-red-950/20 p-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-red-500/40 bg-black text-red-300">
                <AlertTriangle size={18} />
              </div>

              <div>
                <p className="text-sm font-semibold text-white">
                  Admin access required
                </p>
                <p className="mt-1 text-xs text-oa-muted">
                  Only admin and super admin users can save, test, or disconnect
                  provider connections.
                </p>
              </div>
            </div>
          )}

          {actionMessage && (
            <div className="mb-3 rounded border border-oa-border bg-black px-3 py-2 text-xs text-oa-muted">
              {actionMessage}
            </div>
          )}

          <div className="grid gap-3 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded border border-oa-border bg-black">
              <div className="flex items-center justify-between border-b border-oa-border bg-oa-panel px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-teal-300">
                    <Link size={16} />
                  </span>

                  <div>
                    <h3 className="text-[13px] font-semibold text-white">
                      Upstox
                    </h3>
                    <p className="text-[11px] text-oa-muted">
                      API credentials for instruments and historical candles.
                    </p>
                  </div>
                </div>

                <span
                  className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${
                    isConnected
                      ? "border-emerald-500/40 bg-emerald-950/50 text-emerald-200"
                      : "border-zinc-600 bg-zinc-900 text-zinc-200"
                  }`}
                >
                  {isConnected ? "Connected" : "Not Connected"}
                </span>
              </div>

              <form onSubmit={handleSave} className="p-3">
                <div className="grid gap-2 md:grid-cols-2">
                  <Input
                    name="api_key"
                    value={formData.api_key}
                    onChange={handleInputChange}
                    placeholder="Upstox API Key"
                    required
                    disabled={controlsDisabled}
                  />

                  <Input
                    name="api_secret"
                    type="password"
                    value={formData.api_secret}
                    onChange={handleInputChange}
                    placeholder={
                      connection?.has_api_secret
                        ? "API Secret saved - enter only to replace"
                        : "Upstox API Secret"
                    }
                    required={!connection?.has_api_secret}
                    disabled={controlsDisabled}
                  />

                  <Input
                    name="redirect_url"
                    value={formData.redirect_url}
                    onChange={handleInputChange}
                    placeholder="Redirect URL"
                    disabled={controlsDisabled}
                  />

                  <Input
                    name="access_token"
                    type="password"
                    value={formData.access_token}
                    onChange={handleInputChange}
                    placeholder={
                      connection?.has_access_token
                        ? "Access Token saved - enter only to replace"
                        : "Access Token"
                    }
                    required={!connection?.has_access_token}
                    disabled={controlsDisabled}
                  />
                </div>

                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-[11px] text-oa-muted">
                    Only admin and super admin users can manage this connection.
                  </p>

                  <div className="flex items-center gap-2">
                    <Tooltip text="Save credentials" side="top">
                      <button
                        type="submit"
                        disabled={saving || controlsDisabled}
                        className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                        aria-label="Save credentials"
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
                        disabled={testing || !connection || controlsDisabled}
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
                      disabled={!connection || disconnecting || controlsDisabled}
                      onClick={handleDisconnect}
                    />
                  </div>
                </div>
              </form>
            </div>

            <div className="rounded border border-oa-border bg-black">
              <div className="border-b border-oa-border bg-oa-panel px-3 py-2.5">
                <h3 className="text-[13px] font-semibold text-white">
                  Connection Summary
                </h3>
                <p className="text-[11px] text-oa-muted">
                  Current saved provider details.
                </p>
              </div>

              {loading ? (
                <div className="flex items-center justify-center gap-2 px-3 py-8 text-xs text-oa-muted">
                  <Spinner size="sm" color="light" />
                  Loading connection
                </div>
              ) : (
                <div className="space-y-2 p-3 text-xs">
                  <div className="flex items-center justify-between rounded border border-oa-border bg-oa-card px-3 py-2">
                    <span className="text-oa-muted">Provider</span>
                    <span className="font-medium text-white">Upstox</span>
                  </div>

                  <div className="flex items-center justify-between rounded border border-oa-border bg-oa-card px-3 py-2">
                    <span className="text-oa-muted">Control</span>
                    <span className="font-medium text-white">
                      {isAdminControlAllowed ? "Admin Enabled" : "Read Only"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between rounded border border-oa-border bg-oa-card px-3 py-2">
                    <span className="text-oa-muted">API Key</span>
                    <span className="font-medium text-white">
                      {maskValue(connection?.api_key)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between rounded border border-oa-border bg-oa-card px-3 py-2">
                    <span className="text-oa-muted">API Secret</span>
                    <span className="font-medium text-white">
                      {connection?.has_api_secret ? "Saved" : "--"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between rounded border border-oa-border bg-oa-card px-3 py-2">
                    <span className="text-oa-muted">Access Token</span>
                    <span className="font-medium text-white">
                      {connection?.has_access_token ? "Saved" : "--"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between rounded border border-oa-border bg-oa-card px-3 py-2">
                    <span className="text-oa-muted">Last Tested</span>
                    <span className="font-medium text-white">
                      {connection?.last_tested_at || "--"}
                    </span>
                  </div>

                  <div className="rounded border border-emerald-500/30 bg-emerald-950/20 p-3">
                    <div className="mb-2 flex items-center gap-2 text-emerald-200">
                      <ShieldCheck size={15} />
                      <span className="text-[12px] font-semibold">
                        Next Step
                      </span>
                    </div>

                    <p className="text-[11px] leading-5 text-oa-muted">
                      After admin saves this connection, we can add Upstox
                      instrument and candle download controls into DuckDB.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <style>
        {`
          @keyframes oaMenuIn {
            from {
              opacity: 0;
              transform: translateY(-4px) scale(0.98);
            }
            to {
              opacity: 1;
              transform: translateY(0) scale(1);
            }
          }
        `}
      </style>
    </MainLayout>
  );
}

export default Connections;