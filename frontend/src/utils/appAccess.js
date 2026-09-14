export function getAppAccess(user) {
  if (!user) return [];
  if (Array.isArray(user?.app_access)) return user.app_access;
  let restrictions = user?.access_restrictions || [];
  if (typeof restrictions === "string") {
    try { restrictions = JSON.parse(restrictions); } catch { restrictions = []; }
  }
  return ["trading", "admin", "recom"].filter((app) =>
    (app !== "admin" || ["admin", "super_admin"].includes(user?.role)) &&
    !restrictions.includes(`app:deny:${app}`)
  );
}
