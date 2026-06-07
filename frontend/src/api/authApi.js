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

export function requestForgotPasswordOtp(payload) {
  return axiosClient.post("/auth/forgot-password/otp", payload);
}

export function resetPasswordWithOtp(payload) {
  return axiosClient.post("/auth/forgot-password/reset", payload);
}