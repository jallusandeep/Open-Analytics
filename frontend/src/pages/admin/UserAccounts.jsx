import { useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
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

function HeaderFilter({
  label,
  value,
  onChange,
  onClear,
  values = [],
  type = "value"
}) {
  const [open, setOpen] = useState(false);
  const [searchText, setSearchText] = useState("");
  const ref = useRef(null);

  const isActive = value && value !== "all";

  const filteredValues = values.filter((item) =>
    String(item)
      .toLowerCase()
      .includes(searchText.toLowerCase())
  );

  useEffect(() => {
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSelect(selectedValue) {
    onChange(selectedValue);
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative flex items-center justify-between gap-2">
      <span className="truncate">{label}</span>

      <button
        type="button"
        onClick={() => setOpen((previous) => !previous)}
        className={`flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-sm border transition ${
          isActive
            ? "border-oa-border bg-oa-card text-white"
            : "border-oa-border bg-black text-oa-muted hover:bg-oa-card hover:text-white"
        }`}
        aria-label={`Filter ${label}`}
      >
        <Filter size={10} />
      </button>

      {open && (
        <div className="absolute right-2 top-7 z-50 w-64 overflow-hidden rounded border border-oa-border bg-black shadow-2xl animate-[oaMenuIn_0.14s_ease-out]">
          <div className="flex items-center justify-between border-b border-oa-border px-2 py-2">
            <span className="text-[11px] normal-case tracking-normal text-oa-muted">
              Filter {label}
            </span>

            <button
              type="button"
              onClick={() => {
                onClear();
                setSearchText("");
                setOpen(false);
              }}
              className="flex h-6 w-6 items-center justify-center rounded-sm border border-oa-border bg-black text-oa-muted hover:bg-oa-card hover:text-white"
              aria-label="Clear filter"
            >
              <X size={12} />
            </button>
          </div>

          <div className="border-b border-oa-border p-2">
            <div className="flex h-8 items-center gap-2 rounded border border-oa-border bg-black px-2">
              <Search size={13} className="text-oa-muted" />
              <input
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
                placeholder="Search values"
                className="w-full bg-transparent text-xs normal-case tracking-normal text-oa-text outline-none"
                autoFocus={type !== "select"}
              />
            </div>
          </div>

          <div className="max-h-56 overflow-y-auto p-1">
            <button
              type="button"
              onClick={() => handleSelect(type === "select" ? "all" : "")}
              className={`flex h-8 w-full items-center justify-between rounded-sm px-2 text-left text-xs normal-case tracking-normal transition hover:bg-oa-card ${
                !isActive ? "bg-oa-card text-white" : "text-oa-muted"
              }`}
            >
              <span>(All)</span>
              {!isActive && <Check size={12} />}
            </button>

            {filteredValues.length === 0 ? (
              <div className="px-2 py-3 text-center text-[11px] normal-case tracking-normal text-oa-muted">
                No values
              </div>
            ) : (
              filteredValues.map((item) => {
                const selected = value === item;

                return (
                  <button
                    key={item}
                    type="button"
                    onClick={() => handleSelect(item)}
                    className={`flex h-8 w-full items-center justify-between rounded-sm px-2 text-left text-xs normal-case tracking-normal transition hover:bg-oa-card ${
                      selected ? "bg-oa-card text-white" : "text-oa-muted"
                    }`}
                  >
                    <span className="truncate">{item || "--"}</span>
                    {selected && <Check size={12} />}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function uniqueValues(rows, mapper) {
  return Array.from(
    new Set(
      rows
        .map(mapper)
        .filter((value) => value !== null && value !== undefined)
        .map((value) => String(value || "--"))
    )
  ).sort((a, b) => a.localeCompare(b));
}

function UserAccounts() {
  const [users, setUsers] = useState([]);

  const [searchText, setSearchText] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const [columnFilters, setColumnFilters] = useState({
    login_id: "",
    email: "",
    full_name: "",
    mobile_number: "",
    access: ""
  });

  const [page, setPage] = useState(1);
  const [pageSize] = useState(100);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);

  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState("");

  const [showAddForm, setShowAddForm] = useState(false);
  const [saving, setSaving] = useState(false);

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

  async function loadUsers(customPage = page) {
    setLoading(true);
    setActionMessage("");

    try {
      const params = {
        page: customPage,
        page_size: pageSize,
        search: searchText.trim(),
        role: roleFilter
      };

      if (statusFilter !== "all") {
        params.is_active = statusFilter === "active";
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

  const accessTextForUser = (user) =>
    user.role === "user" ? user.access_restrictions || "[]" : "Full Access";

  const headerValues = useMemo(() => {
    return {
      login_id: uniqueValues(users, (user) => user.login_id || "--"),
      email: uniqueValues(users, (user) => user.email || "--"),
      full_name: uniqueValues(users, (user) => user.full_name || "--"),
      mobile_number: uniqueValues(users, (user) => user.mobile_number || "--"),
      role: uniqueValues(users, (user) => user.role || "--"),
      status: uniqueValues(users, (user) =>
        user.is_active ? "active" : "inactive"
      ),
      access: uniqueValues(users, accessTextForUser)
    };
  }, [users]);

  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      const accessText = accessTextForUser(user);
      const statusText = user.is_active ? "active" : "inactive";

      return (
        String(user.login_id || "--")
          .toLowerCase()
          .includes(columnFilters.login_id.toLowerCase()) &&
        String(user.email || "--")
          .toLowerCase()
          .includes(columnFilters.email.toLowerCase()) &&
        String(user.full_name || "--")
          .toLowerCase()
          .includes(columnFilters.full_name.toLowerCase()) &&
        String(user.mobile_number || "--")
          .toLowerCase()
          .includes(columnFilters.mobile_number.toLowerCase()) &&
        String(accessText || "")
          .toLowerCase()
          .includes(columnFilters.access.toLowerCase()) &&
        (roleFilter === "all" || user.role === roleFilter) &&
        (statusFilter === "all" || statusText === statusFilter)
      );
    });
  }, [users, columnFilters, roleFilter, statusFilter]);

  function handleColumnFilterChange(name, value) {
    setColumnFilters((previous) => ({
      ...previous,
      [name]: value === "--" ? "" : value
    }));
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
            <div className="flex h-8 w-[360px] max-w-full items-center gap-2 rounded border border-oa-border bg-black px-2">
              <Search size={14} className="text-oa-muted" />

              <input
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
                placeholder="Search users"
                className="w-full bg-transparent text-xs outline-none"
              />
            </div>

            <Select
              value={roleFilter}
              onChange={(event) => setRoleFilter(event.target.value)}
              options={roleOptions}
              ariaLabel="Role filter"
              minWidth="w-36"
            />

            <Select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              options={statusOptions}
              ariaLabel="Status filter"
              minWidth="w-36"
            />

            <IconButton
              icon={Search}
              label="Search"
              type="submit"
              variant="search"
              tooltipSide="top"
              disabled={loading}
            />

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

          <div className="overflow-visible rounded border border-oa-border bg-black oa-table-font">
            <div className="min-w-[1080px]">
              <div className="grid grid-cols-[120px_1.4fr_1.4fr_130px_120px_105px_160px_60px] border-b border-oa-border bg-oa-panel px-3 py-2 text-[10px] uppercase tracking-widest text-oa-muted">
                <HeaderFilter
                  label="Login ID"
                  value={columnFilters.login_id}
                  values={headerValues.login_id}
                  onChange={(value) =>
                    handleColumnFilterChange("login_id", value)
                  }
                  onClear={() => handleColumnFilterChange("login_id", "")}
                />

                <HeaderFilter
                  label="Email ID"
                  value={columnFilters.email}
                  values={headerValues.email}
                  onChange={(value) =>
                    handleColumnFilterChange("email", value)
                  }
                  onClear={() => handleColumnFilterChange("email", "")}
                />

                <HeaderFilter
                  label="Full Name"
                  value={columnFilters.full_name}
                  values={headerValues.full_name}
                  onChange={(value) =>
                    handleColumnFilterChange("full_name", value)
                  }
                  onClear={() => handleColumnFilterChange("full_name", "")}
                />

                <HeaderFilter
                  label="Mobile"
                  value={columnFilters.mobile_number}
                  values={headerValues.mobile_number}
                  onChange={(value) =>
                    handleColumnFilterChange("mobile_number", value)
                  }
                  onClear={() =>
                    handleColumnFilterChange("mobile_number", "")
                  }
                />

                <HeaderFilter
                  label="Role"
                  value={roleFilter}
                  values={headerValues.role}
                  type="select"
                  onChange={(value) => setRoleFilter(value)}
                  onClear={() => setRoleFilter("all")}
                />

                <HeaderFilter
                  label="Status"
                  value={statusFilter}
                  values={headerValues.status}
                  type="select"
                  onChange={(value) => setStatusFilter(value)}
                  onClear={() => setStatusFilter("all")}
                />

                <HeaderFilter
                  label="Access"
                  value={columnFilters.access}
                  values={headerValues.access}
                  onChange={(value) =>
                    handleColumnFilterChange("access", value)
                  }
                  onClear={() => handleColumnFilterChange("access", "")}
                />

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
                      className="grid grid-cols-[120px_1.4fr_1.4fr_130px_120px_105px_160px_60px] border-b border-oa-border px-3 py-1.5 text-[11px] last:border-b-0 hover:bg-oa-panel/60"
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
                          className={`rounded-full border px-2 py-0.5 text-[10px] ${getRolePill(
                            user.role
                          )}`}
                        >
                          {user.role}
                        </span>
                      </span>

                      <span>
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] ${getStatusPill(
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