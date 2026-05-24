import { useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Filter,
  Plus,
  RefreshCcw,
  Search,
  Trash2,
  X
} from "lucide-react";

import {
  createAdminUser,
  deleteAdminUser,
  getAdminUsers
} from "../../api/adminApi";
import MainLayout from "../../components/layout/MainLayout";
import Spinner from "../../components/common/Spinner";
import IconButton from "../../components/common/IconButton";
import Select from "../../components/common/Select";
import TableFilterDropdown from "../../components/common/TableFilterDropdown";

const tableColumns = [
  { key: "login_id", label: "Login ID" },
  { key: "email", label: "Email ID" },
  { key: "full_name", label: "Full Name" },
  { key: "mobile_number", label: "Mobile" },
  { key: "role", label: "Role" },
  { key: "status", label: "Status" },
  { key: "access", label: "Access" }
];

const gridTemplateColumns =
  "120px minmax(180px,1.4fr) minmax(180px,1.4fr) 130px 120px 105px 160px 60px";

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

function accessTextForUser(user) {
  return user.role === "user"
    ? user.access_restrictions || "[]"
    : "Full Access";
}

function getColumnValue(user, key) {
  if (key === "status") {
    return user.is_active ? "active" : "inactive";
  }

  if (key === "role") {
    return formatRoleLabel(user.role);
  }

  if (key === "access") {
    return accessTextForUser(user);
  }

  return user[key];
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

function UserAccounts() {
  const [users, setUsers] = useState([]);

  const [searchText, setSearchText] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const [columnFilters, setColumnFilters] = useState({});
  const [draftColumnFilters, setDraftColumnFilters] = useState({});
  const [activeFilter, setActiveFilter] = useState(null);
  const [sortConfig, setSortConfig] = useState({
    key: null,
    direction: null
  });

  const [page, setPage] = useState(1);
  const [pageSize] = useState(100);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);

  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState("");

  const [showAddForm, setShowAddForm] = useState(false);
  const [saving, setSaving] = useState(false);

  const filterRef = useRef(null);

  const [formData, setFormData] = useState({
    login_id: "",
    full_name: "",
    email: "",
    mobile_number: "",
    password: "",
    role: "user",
    access_restrictions: []
  });

  const roleOptions = [
    { value: "all", label: "All Roles" },
    { value: "super_admin", label: "Super Admin" },
    { value: "admin", label: "Admin" },
    { value: "user", label: "User" }
  ];

  const statusOptions = [
    { value: "all", label: "All Status" },
    { value: "active", label: "Active" },
    { value: "inactive", label: "Inactive" }
  ];

  async function loadUsers(customPage = page, overrides = {}) {
    setLoading(true);
    setActionMessage("");

    const effectiveSearchText =
      overrides.searchText !== undefined ? overrides.searchText : searchText;

    const effectiveRoleFilter =
      overrides.roleFilter !== undefined ? overrides.roleFilter : roleFilter;

    const effectiveStatusFilter =
      overrides.statusFilter !== undefined
        ? overrides.statusFilter
        : statusFilter;

    try {
      const params = {
        page: customPage,
        page_size: pageSize,
        search: effectiveSearchText.trim(),
        role: effectiveRoleFilter
      };

      if (effectiveStatusFilter !== "all") {
        params.is_active = effectiveStatusFilter === "active";
      }

      const response = await getAdminUsers(params);

      setUsers(response.data.users);
      setPage(response.data.page);
      setTotalPages(response.data.total_pages);
      setTotalRecords(response.data.total_records);
    } catch (error) {
      setActionMessage(
        error.response?.data?.detail || "Unable to load user accounts."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    function handleClickOutside(event) {
      if (filterRef.current && !filterRef.current.contains(event.target)) {
        setActiveFilter(null);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const headerValues = useMemo(() => {
    return tableColumns.reduce((result, column) => {
      result[column.key] = getFilterValues(users, column.key);
      return result;
    }, {});
  }, [users]);

  const filteredUsers = useMemo(() => {
    let result = users.filter((user) => {
      return Object.entries(columnFilters).every(([key, selectedValues]) => {
        if (!selectedValues || selectedValues.length === 0) {
          return true;
        }

        const value = normalizeCellValue(getColumnValue(user, key));
        return selectedValues.includes(value);
      });
    });

    if (roleFilter !== "all") {
      result = result.filter((user) => user.role === roleFilter);
    }

    if (statusFilter !== "all") {
      result = result.filter((user) => {
        const statusText = user.is_active ? "active" : "inactive";
        return statusText === statusFilter;
      });
    }

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
  }, [users, columnFilters, roleFilter, statusFilter, sortConfig]);

  function hasAnyActiveFilter() {
    return (
      searchText.trim() !== "" ||
      roleFilter !== "all" ||
      statusFilter !== "all" ||
      sortConfig.key !== null ||
      Object.values(columnFilters).some(
        (value) => Array.isArray(value) && value.length > 0
      )
    );
  }

  function clearAllFilters() {
    setSearchText("");
    setRoleFilter("all");
    setStatusFilter("all");
    setColumnFilters({});
    setDraftColumnFilters({});
    setSortConfig({
      key: null,
      direction: null
    });
    setActiveFilter(null);

    loadUsers(1, {
      searchText: "",
      roleFilter: "all",
      statusFilter: "all"
    });
  }

  function clearSearchFilter() {
    setSearchText("");

    loadUsers(1, {
      searchText: ""
    });
  }

  function clearRoleFilter() {
    setRoleFilter("all");

    loadUsers(1, {
      roleFilter: "all"
    });
  }

  function clearStatusFilter() {
    setStatusFilter("all");

    loadUsers(1, {
      statusFilter: "all"
    });
  }

  function openColumnFilter(key) {
    setDraftColumnFilters((previous) => ({
      ...previous,
      [key]: columnFilters[key] || []
    }));

    setActiveFilter((previous) => (previous === key ? null : key));
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

  function handleInputChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value
    }));
  }

  async function handleCreateUser(event) {
    event.preventDefault();
    setSaving(true);
    setActionMessage("");

    try {
      await createAdminUser({
        ...formData,
        access_restrictions:
          formData.role === "user" ? formData.access_restrictions : []
      });

      setShowAddForm(false);
      setFormData({
        login_id: "",
        full_name: "",
        email: "",
        mobile_number: "",
        password: "",
        role: "user",
        access_restrictions: []
      });

      setActionMessage("User created successfully.");
      loadUsers(1);
    } catch (error) {
      setActionMessage(
        error.response?.data?.detail || "Unable to create user."
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteUser(userId) {
    const confirmDelete = window.confirm(
      "Are you sure you want to deactivate this user?"
    );

    if (!confirmDelete) {
      return;
    }

    setActionMessage("");

    try {
      await deleteAdminUser(userId);
      setActionMessage("User deactivated successfully.");
      loadUsers(page);
    } catch (error) {
      setActionMessage(
        error.response?.data?.detail || "Unable to deactivate user."
      );
    }
  }

  function handleSearchSubmit(event) {
    event.preventDefault();
    loadUsers(1);
  }

  function getRolePill(role) {
    const roleClass = {
      super_admin: "border-purple-500/40 bg-purple-950/50 text-purple-200",
      admin: "border-sky-500/40 bg-sky-950/50 text-sky-200",
      user: "border-zinc-600 bg-zinc-900 text-zinc-200"
    };

    return roleClass[role] || roleClass.user;
  }

  function getStatusPill(isActive) {
    return isActive
      ? "border-emerald-500/40 bg-emerald-950/50 text-emerald-200"
      : "border-red-500/40 bg-red-950/50 text-red-200";
  }

  return (
    <MainLayout>
      <section className="p-3">
        <div className="rounded border border-oa-border bg-oa-card p-3">
          <div className="mb-3">
            <h2 className="text-sm font-semibold">User Accounts</h2>
            <p className="text-[11px] text-oa-muted">
              Manage users, roles, restrictions, and active status.
            </p>
          </div>

          <form
            onSubmit={handleSearchSubmit}
            className="mb-3 flex flex-wrap items-center gap-2"
          >
            <div className="relative flex h-8 w-[360px] max-w-full items-center gap-2 rounded border border-oa-border bg-black px-2">
              <Search size={14} className="text-oa-muted" />

              <input
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
                placeholder="Search users"
                className="w-full bg-transparent pr-6 text-xs outline-none"
              />

              {searchText.trim() !== "" && (
                <button
                  type="button"
                  onClick={clearSearchFilter}
                  className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded-sm border border-oa-border bg-black text-oa-muted transition hover:bg-oa-card hover:text-white"
                  aria-label="Clear search"
                  title="Clear search"
                >
                  <X size={11} />
                </button>
              )}
            </div>

            <div className="relative">
              <Select
                value={roleFilter}
                onChange={(event) => setRoleFilter(event.target.value)}
                options={roleOptions}
                ariaLabel="Role filter"
                minWidth="w-36"
              />

              {roleFilter !== "all" && (
                <button
                  type="button"
                  onClick={clearRoleFilter}
                  className="absolute -right-2 -top-2 flex h-4 w-4 items-center justify-center rounded-full border border-oa-border bg-black text-oa-muted shadow transition hover:bg-oa-card hover:text-white"
                  aria-label="Clear role filter"
                  title="Clear role filter"
                >
                  <X size={9} />
                </button>
              )}
            </div>

            <div className="relative">
              <Select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                options={statusOptions}
                ariaLabel="Status filter"
                minWidth="w-36"
              />

              {statusFilter !== "all" && (
                <button
                  type="button"
                  onClick={clearStatusFilter}
                  className="absolute -right-2 -top-2 flex h-4 w-4 items-center justify-center rounded-full border border-oa-border bg-black text-oa-muted shadow transition hover:bg-oa-card hover:text-white"
                  aria-label="Clear status filter"
                  title="Clear status filter"
                >
                  <X size={9} />
                </button>
              )}
            </div>

            <IconButton
              icon={Search}
              label="Search"
              type="submit"
              variant="search"
              tooltipSide="top"
              disabled={loading}
            />

            {hasAnyActiveFilter() && (
              <IconButton
                icon={X}
                label="Clear filters"
                variant="default"
                tooltipSide="top"
                onClick={clearAllFilters}
              />
            )}

            <div className="ml-auto flex items-center gap-2">
              <IconButton
                icon={RefreshCcw}
                label="Refresh"
                variant="refresh"
                tooltipSide="top"
                onClick={() => loadUsers(page)}
              />

              <IconButton
                icon={Plus}
                label="Add"
                variant="add"
                tooltipSide="top"
                onClick={() => setShowAddForm((value) => !value)}
              />
            </div>
          </form>

          {showAddForm && (
            <form
              onSubmit={handleCreateUser}
              className="mb-3 rounded border border-oa-border bg-black p-3"
            >
              <div className="mb-3 grid gap-2 md:grid-cols-3">
                <input
                  name="login_id"
                  value={formData.login_id}
                  onChange={handleInputChange}
                  placeholder="Login ID"
                  className="h-8 rounded border border-oa-border bg-oa-card px-2 text-xs outline-none"
                  required
                />

                <input
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleInputChange}
                  placeholder="Full Name"
                  className="h-8 rounded border border-oa-border bg-oa-card px-2 text-xs outline-none"
                  required
                />

                <input
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="Email ID"
                  className="h-8 rounded border border-oa-border bg-oa-card px-2 text-xs outline-none"
                  required
                />

                <input
                  name="mobile_number"
                  value={formData.mobile_number}
                  onChange={handleInputChange}
                  placeholder="Mobile Number"
                  className="h-8 rounded border border-oa-border bg-oa-card px-2 text-xs outline-none"
                />

                <input
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  placeholder="Password"
                  className="h-8 rounded border border-oa-border bg-oa-card px-2 text-xs outline-none"
                  required
                />

                <Select
                  value={formData.role}
                  onChange={(event) =>
                    setFormData((previous) => ({
                      ...previous,
                      role: event.target.value
                    }))
                  }
                  options={[
                    { value: "user", label: "User" },
                    { value: "admin", label: "Admin" },
                    { value: "super_admin", label: "Super Admin" }
                  ]}
                  ariaLabel="New user role"
                  minWidth="w-full"
                />
              </div>

              <div className="flex justify-end gap-2">
                <IconButton
                  icon={X}
                  label="Cancel"
                  variant="default"
                  tooltipSide="top"
                  onClick={() => setShowAddForm(false)}
                />

                <button
                  type="submit"
                  disabled={saving}
                  className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-white text-black transition hover:bg-zinc-200 disabled:opacity-60"
                  aria-label="Save user"
                >
                  {saving ? (
                    <Spinner size="xs" color="dark" />
                  ) : (
                    <Plus size={15} />
                  )}
                </button>
              </div>
            </form>
          )}

          {actionMessage && (
            <div className="mb-3 rounded border border-oa-border bg-black px-3 py-2 text-xs text-oa-muted">
              {actionMessage}
            </div>
          )}

          <div className="overflow-hidden rounded border border-oa-border bg-black oa-table-font">
            <div className="min-w-[1080px]">
              <div
                ref={filterRef}
                className="grid border-b border-oa-border bg-oa-panel px-3 py-2.5 text-[11px] font-bold uppercase tracking-wider text-oa-muted"
                style={{ gridTemplateColumns }}
              >
                {tableColumns.map((column) => {
                  const active = isColumnFilterActive(column.key);

                  return (
                    <div
                      key={column.key}
                      className="relative flex min-w-0 items-center justify-between gap-2 pr-8"
                    >
                      <span className="truncate">{column.label}</span>

                      <button
                        type="button"
                        onClick={() => openColumnFilter(column.key)}
                        className={`absolute right-3 top-1/2 flex h-[22px] w-[22px] -translate-y-1/2 items-center justify-center rounded-sm border transition ${
                          active
                            ? "border-oa-border bg-oa-card text-white"
                            : "border-oa-border bg-black text-oa-muted hover:bg-oa-card hover:text-white"
                        }`}
                        aria-label={`Filter ${column.label}`}
                        title={`Filter ${column.label}`}
                      >
                        <Filter size={10} />

                        {active && (
                          <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full border border-black bg-emerald-400" />
                        )}
                      </button>

                      {activeFilter === column.key && (
                        <div
                          className={`absolute top-7 z-50 ${
                            ["role", "status", "access"].includes(column.key)
                              ? "right-3"
                              : "left-0"
                          }`}
                        >
                          <TableFilterDropdown
                            columnName={column.label}
                            values={headerValues[column.key] || []}
                            selectedValues={columnFilters[column.key] || []}
                            pendingValues={draftColumnFilters[column.key] || []}
                            align={
                              ["role", "status", "access"].includes(column.key)
                                ? "right"
                                : "left"
                            }
                            onChange={(values) =>
                              setDraftColumnFilters((previous) => ({
                                ...previous,
                                [column.key]: values
                              }))
                            }
                            onApply={() => applyColumnFilter(column.key)}
                            onCancel={() => setActiveFilter(null)}
                            onSortAsc={() => handleSort(column.key, "asc")}
                            onSortDesc={() => handleSort(column.key, "desc")}
                            onClear={() => clearColumnFilter(column.key)}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}

                <span className="text-center">Action</span>
              </div>

              {loading ? (
                <div className="flex items-center justify-center gap-2 px-3 py-8 text-xs text-oa-muted">
                  <Spinner size="sm" color="light" />
                  Loading users
                </div>
              ) : filteredUsers.length === 0 ? (
                <div className="px-3 py-8 text-center text-xs text-oa-muted">
                  No users found.
                </div>
              ) : (
                filteredUsers.map((user) => {
                  const accessText = accessTextForUser(user);

                  return (
                    <div
                      key={user.user_id}
                      className="grid items-center border-b border-oa-border px-3 py-2 text-[13px] last:border-b-0 hover:bg-oa-panel/60"
                      style={{ gridTemplateColumns }}
                    >
                      <span className="truncate font-semibold">
                        {user.login_id || "--"}
                      </span>

                      <span className="truncate">{user.email}</span>

                      <span className="truncate">{user.full_name}</span>

                      <span className="truncate">
                        {user.mobile_number || "--"}
                      </span>

                      <span>
                        <span
                          className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${getRolePill(
                            user.role
                          )}`}
                        >
                          {formatRoleLabel(user.role)}
                        </span>
                      </span>

                      <span>
                        <span
                          className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${getStatusPill(
                            user.is_active
                          )}`}
                        >
                          {user.is_active ? "active" : "inactive"}
                        </span>
                      </span>

                      <span className="truncate">{accessText}</span>

                      <span className="flex justify-center">
                        <IconButton
                          icon={Trash2}
                          label="Deactivate"
                          variant="danger"
                          tooltipSide="left"
                          onClick={() => handleDeleteUser(user.user_id)}
                        />
                      </span>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div className="mt-3 flex flex-col gap-2 text-xs text-oa-muted md:flex-row md:items-center md:justify-between">
            <span>
              Records: {totalRecords} | Page {page} of {totalPages}
            </span>

            <div className="flex items-center gap-2">
              <IconButton
                icon={ChevronLeft}
                label="Previous"
                variant="default"
                disabled={page <= 1 || loading}
                onClick={() => loadUsers(page - 1)}
                tooltipSide="top"
              />

              <IconButton
                icon={ChevronRight}
                label="Next"
                variant="default"
                disabled={page >= totalPages || loading}
                onClick={() => loadUsers(page + 1)}
                tooltipSide="top"
              />
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

export default UserAccounts;