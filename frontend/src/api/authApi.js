import axiosClient from "./axiosClient";

export function loginUser(payload) {
  return axiosClient.post("/auth/login", payload);
}

export function registerUser(payload) {
  return axiosClient.post("/auth/register", payload);
}

export function getCurrentUser() {
  return axiosClient.get("/users/me");
}