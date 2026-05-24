import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Pencil,
  Plus,
  RefreshCcw,
  Trash2,
  X
} from "lucide-react";

import {
  createAdminUser,
  deleteAdminUser,
  getAdminUsers,
  updateAdminUser
} from "../../api/adminApi";
import MainLayout from "../../components/layout/MainLayout";
import Spinner from "../../components/common/Spinner";
import IconButton from "../../components/common/IconButton";
import Input from "../../components/common/Input";
import Select from "../../components/common/Select";
import Modal from "../../components/common/Modal";
import Tooltip from "../../components/common/Tooltip";
import DataTable from "../../components/tables/DataTable";
import TableToolbar from "../../components/tables/TableToolbar";

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
  "120px minmax(180px,1.4fr) minmax(180px,1.4fr) 130px 120px 105px 160px 86px";

const emptyFormData = {
  login_id: "",
  full_name: "",
  email: "",
  mobile_number: "",
  password: "",
  role: "user",
  is_active: true,
  access_restrictions: []
};

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

function parseAccessRestrictions(value) {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value;
  }

  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function UserAccounts() {
  const [users, setUsers] = useState([]);

  const [searchText, setSearchText] = useState("");
  const [appliedSearchText, setAppliedSearchText] = useState("");
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

  const [showAddModal, setShowAddModal] = useState(false);
  const [saving, setSaving] = useState(false);

  const [editUser, setEditUser] = useState(null);
  const [updating, setUpdating] = useState(false);

  const [deleteUser, setDeleteUser] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const [formData, setFormData] = useState(emptyFormData);
  const [editFormData, setEditFormData] = useState(emptyFormData);

  const currentUser = useMemo(() => getStoredCurrentUser(), []);
  const currentUserRole = currentUser?.role;

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

  const editRoleOptions =
    currentUserRole === "admin"
      ? [{ value: "user", label: "User" }]
      : [
          { value: "user", label: "User" },
          { value: "admin", label: "Admin" },
          { value: "super_admin", label: "Super Admin" }
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
      appliedSearchText.trim() !== "" ||
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
    setAppliedSearchText("");
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
    setAppliedSearchText("");

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

  function openCreateModal() {
    setActionMessage("");
    setShowAddModal(true);
  }

  function closeCreateModal() {
    if (saving) {
      return;
    }

    setShowAddModal(false);
    setFormData(emptyFormData);
  }

  function canEditUser(user) {
    if (!["admin", "super_admin"].includes(currentUserRole)) {
      return false;
    }

    if (user.user_id === currentUser?.user_id) {
      return false;
    }

    if (currentUserRole === "admin" && user.role === "super_admin") {
      return false;
    }

    return true;
  }

  function openEditModal(user) {
    setActionMessage("");

    if (!canEditUser(user)) {
      setActionMessage(
        user.user_id === currentUser?.user_id
          ? "You cannot edit your own account from User Accounts."
          : "You do not have permission to edit this user."
      );
      return;
    }

    setEditUser(user);
    setEditFormData({
      login_id: user.login_id || "",
      full_name: user.full_name || "",
      email: user.email || "",
      mobile_number: user.mobile_number || "",
      password: "",
      role: user.role || "user",
      is_active: Boolean(user.is_active),
      access_restrictions: parseAccessRestrictions(user.access_restrictions)
    });
  }

  function closeEditModal() {
    if (updating) {
      return;
    }

    setEditUser(null);
    setEditFormData(emptyFormData);
  }

  function openDeleteModal(user) {
    setActionMessage("");
    setDeleteUser(user);
  }

  function closeDeleteModal() {
    if (deleting) {
      return;
    }

    setDeleteUser(null);
  }

  function handleInputChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value
    }));
  }

  function handleEditInputChange(event) {
    const { name, value } = event.target;

    setEditFormData((previous) => ({
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

      setShowAddModal(false);
      setFormData(emptyFormData);

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

  async function handleUpdateUser(event) {
    event.preventDefault();

    if (!editUser) {
      return;
    }

    setUpdating(true);
    setActionMessage("");

    try {
      await updateAdminUser(editUser.user_id, {
        login_id: editFormData.login_id,
        full_name: editFormData.full_name,
        email: editFormData.email,
        mobile_number: editFormData.mobile_number,
        role: editFormData.role,
        is_active: editFormData.is_active,
        access_restrictions:
          editFormData.role === "user"
            ? editFormData.access_restrictions
            : []
      });

      setEditUser(null);
      setEditFormData(emptyFormData);
      setActionMessage("User updated successfully.");
      loadUsers(page);
    } catch (error) {
      setActionMessage(
        error.response?.data?.detail || "Unable to update user."
      );
    } finally {
      setUpdating(false);
    }
  }

  async function confirmDeleteUser() {
    if (!deleteUser) {
      return;
    }

    setDeleting(true);
    setActionMessage("");

    try {
      await deleteAdminUser(deleteUser.user_id);
      setActionMessage("User deleted successfully.");
      setDeleteUser(null);
      loadUsers(page);
    } catch (error) {
      setActionMessage(
        error.response?.data?.detail || "Unable to deactivate user."
      );
    } finally {
      setDeleting(false);
    }
  }

  function handleSearchSubmit(event) {
    event.preventDefault();
    setAppliedSearchText(searchText.trim());
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

  function renderUserCell(user, column) {
    const accessText = accessTextForUser(user);

    if (column.key === "login_id") {
      return (
        <span key={column.key} className="truncate font-semibold">
          {user.login_id || "--"}
        </span>
      );
    }

    if (column.key === "email") {
      return (
        <span key={column.key} className="truncate">
          {user.email}
        </span>
      );
    }

    if (column.key === "full_name") {
      return (
        <span key={column.key} className="truncate">
          {user.full_name}
        </span>
      );
    }

    if (column.key === "mobile_number") {
      return (
        <span key={column.key} className="truncate">
          {user.mobile_number || "--"}
        </span>
      );
    }

    if (column.key === "role") {
      return (
        <span key={column.key}>
          <span
            className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${getRolePill(
              user.role
            )}`}
          >
            {formatRoleLabel(user.role)}
          </span>
        </span>
      );
    }

    if (column.key === "status") {
      return (
        <span key={column.key}>
          <span
            className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${getStatusPill(
              user.is_active
            )}`}
          >
            {user.is_active ? "active" : "inactive"}
          </span>
        </span>
      );
    }

    return (
      <span key={column.key} className="truncate">
        {accessText}
      </span>
    );
  }

  function renderUserActions(user) {
    return (
      <span className="flex items-center justify-center gap-1">
        {canEditUser(user) && (
          <IconButton
            icon={Pencil}
            label="Edit"
            variant="default"
            tooltipSide="left"
            onClick={() => openEditModal(user)}
          />
        )}

        <IconButton
          icon={Trash2}
          label="Delete"
          variant="danger"
          tooltipSide="left"
          onClick={() => openDeleteModal(user)}
        />
      </span>
    );
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

          <TableToolbar
            searchValue={searchText}
            onSearchChange={setSearchText}
            onSearchClear={clearSearchFilter}
            onSearchSubmit={handleSearchSubmit}
            searchActive={appliedSearchText.trim() !== ""}
            searchPlaceholder="Search users"
            filters={[
              {
                value: roleFilter,
                onChange: (event) => setRoleFilter(event.target.value),
                options: roleOptions,
                onClear: clearRoleFilter,
                showClear: roleFilter !== "all",
                ariaLabel: "Role filter",
                minWidth: "w-36"
              },
              {
                value: statusFilter,
                onChange: (event) => setStatusFilter(event.target.value),
                options: statusOptions,
                onClear: clearStatusFilter,
                showClear: statusFilter !== "all",
                ariaLabel: "Status filter",
                minWidth: "w-36"
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
                onClick: () => loadUsers(page)
              },
              {
                icon: Plus,
                label: "Add",
                variant: "add",
                onClick: openCreateModal
              }
            ]}
          />

          {actionMessage && (
            <div className="mb-3 rounded border border-oa-border bg-black px-3 py-2 text-xs text-oa-muted">
              {actionMessage}
            </div>
          )}

          <DataTable
            columns={tableColumns}
            rows={filteredUsers}
            loading={loading}
            loadingMessage="Loading users"
            emptyMessage="No users found."
            gridTemplateColumns={gridTemplateColumns}
            getRowKey={(user) => user.user_id}
            renderCell={renderUserCell}
            renderActions={renderUserActions}
            filterConfig={{
              activeFilter,
              headerValues,
              columnFilters,
              draftColumnFilters,
              rightAlignedKeys: ["role", "status", "access"],
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

      <Modal
        open={showAddModal}
        title="Add User"
        subtitle="Create a new Open Analytics user account."
        onClose={closeCreateModal}
        width="max-w-2xl"
        closeOnOverlay={!saving}
        footer={
          <>
            <IconButton
              icon={X}
              label="Cancel"
              variant="danger"
              tooltipSide="top"
              disabled={saving}
              onClick={closeCreateModal}
            />

            <Tooltip text="Save user" side="top">
              <button
                type="submit"
                form="create-user-form"
                disabled={saving}
                className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                aria-label="Save user"
              >
                {saving ? (
                  <Spinner size="xs" color="light" />
                ) : (
                  <Check size={15} />
                )}
              </button>
            </Tooltip>
          </>
        }
      >
        <form id="create-user-form" onSubmit={handleCreateUser}>
          <div className="grid gap-2 md:grid-cols-3">
            <Input
              name="login_id"
              value={formData.login_id}
              onChange={handleInputChange}
              placeholder="Login ID"
              required
            />

            <Input
              name="full_name"
              value={formData.full_name}
              onChange={handleInputChange}
              placeholder="Full Name"
              required
            />

            <Input
              name="email"
              type="email"
              value={formData.email}
              onChange={handleInputChange}
              placeholder="Email ID"
              required
            />

            <Input
              name="mobile_number"
              value={formData.mobile_number}
              onChange={handleInputChange}
              placeholder="Mobile Number"
            />

            <Input
              name="password"
              type="password"
              value={formData.password}
              onChange={handleInputChange}
              placeholder="Password"
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
        </form>
      </Modal>

      <Modal
        open={Boolean(editUser)}
        title="Edit User"
        subtitle="Update user account details, role, and active status."
        onClose={closeEditModal}
        width="max-w-2xl"
        closeOnOverlay={!updating}
        footer={
          <>
            <IconButton
              icon={X}
              label="Cancel"
              variant="danger"
              tooltipSide="top"
              disabled={updating}
              onClick={closeEditModal}
            />

            <Tooltip text="Update user" side="top">
              <button
                type="submit"
                form="edit-user-form"
                disabled={updating}
                className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                aria-label="Update user"
              >
                {updating ? (
                  <Spinner size="xs" color="light" />
                ) : (
                  <Check size={15} />
                )}
              </button>
            </Tooltip>
          </>
        }
      >
        <form id="edit-user-form" onSubmit={handleUpdateUser}>
          <div className="grid gap-2 md:grid-cols-3">
            <Input
              name="login_id"
              value={editFormData.login_id}
              onChange={handleEditInputChange}
              placeholder="Login ID"
              required
            />

            <Input
              name="full_name"
              value={editFormData.full_name}
              onChange={handleEditInputChange}
              placeholder="Full Name"
              required
            />

            <Input
              name="email"
              type="email"
              value={editFormData.email}
              onChange={handleEditInputChange}
              placeholder="Email ID"
              required
            />

            <Input
              name="mobile_number"
              value={editFormData.mobile_number}
              onChange={handleEditInputChange}
              placeholder="Mobile Number"
            />

            <Select
              value={editFormData.role}
              onChange={(event) =>
                setEditFormData((previous) => ({
                  ...previous,
                  role: event.target.value
                }))
              }
              options={editRoleOptions}
              ariaLabel="Edit user role"
              minWidth="w-full"
            />

            <Select
              value={editFormData.is_active ? "active" : "inactive"}
              onChange={(event) =>
                setEditFormData((previous) => ({
                  ...previous,
                  is_active: event.target.value === "active"
                }))
              }
              options={[
                { value: "active", label: "Active" },
                { value: "inactive", label: "Inactive" }
              ]}
              ariaLabel="Edit user status"
              minWidth="w-full"
            />
          </div>

          {currentUserRole === "admin" && editUser?.role === "admin" && (
            <p className="mt-3 rounded border border-amber-500/30 bg-amber-950/20 px-3 py-2 text-xs text-amber-200">
              Admin users cannot assign admin or super admin roles.
            </p>
          )}
        </form>
      </Modal>

      <Modal
        open={Boolean(deleteUser)}
        title="Delete User"
        subtitle="Please confirm before deleting this user."
        onClose={closeDeleteModal}
        width="max-w-md"
        closeOnOverlay={!deleting}
        footer={
          <>
            <IconButton
              icon={X}
              label="Cancel"
              variant="danger"
              tooltipSide="top"
              disabled={deleting}
              onClick={closeDeleteModal}
            />

            <Tooltip text="Confirm delete" side="top">
              <button
                type="button"
                onClick={confirmDeleteUser}
                disabled={deleting}
                className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                aria-label="Confirm delete"
              >
                {deleting ? (
                  <Spinner size="xs" color="light" />
                ) : (
                  <Check size={15} />
                )}
              </button>
            </Tooltip>
          </>
        }
      >
        <div className="flex gap-3 rounded border border-red-500/30 bg-red-950/20 p-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-red-500/40 bg-black text-red-300">
            <AlertTriangle size={18} />
          </div>

          <div className="min-w-0">
            <p className="text-sm font-semibold text-white">
              Are you sure you want to delete this user?
            </p>

            <div className="mt-2 space-y-1 text-xs text-oa-muted">
              <p>
                <span className="text-oa-text">Name:</span>{" "}
                {deleteUser?.full_name || "--"}
              </p>

              <p>
                <span className="text-oa-text">Email:</span>{" "}
                {deleteUser?.email || "--"}
              </p>

              <p>
                <span className="text-oa-text">Role:</span>{" "}
                {formatRoleLabel(deleteUser?.role)}
              </p>
            </div>

            <p className="mt-3 text-[11px] text-red-300">
              This will remove this user from the User Accounts list.
            </p>
          </div>
        </div>
      </Modal>

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
