import axiosClient from "./axiosClient";

export function getMyProfile() {
  return axiosClient.get("/auth/me");
}

export function updateMyProfile(payload) {
  return axiosClient.put("/auth/me", payload);
}

export function changeMyPassword(payload) {
  return axiosClient.put("/auth/password", payload);
}