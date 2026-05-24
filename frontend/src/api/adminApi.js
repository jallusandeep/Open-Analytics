import axiosClient from "./axiosClient";

export function getAdminUsers(params) {
  return axiosClient.get("/admin/users", {
    params
  });
}

export function createAdminUser(payload) {
  return axiosClient.post("/admin/users", payload);
}

export function deleteAdminUser(userId) {
  return axiosClient.delete(`/admin/users/${userId}`);
}