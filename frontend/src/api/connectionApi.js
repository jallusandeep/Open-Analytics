import axiosClient from "./axiosClient";

export function getConnections() {
  return axiosClient.get("/connections");
}

export function saveUpstoxConnection(payload) {
  return axiosClient.post("/connections/upstox", payload);
}

export function getUpstoxAuthorizeUrl() {
  return axiosClient.get("/connections/upstox/authorize-url");
}

export function exchangeUpstoxAuthCode(payload) {
  return axiosClient.post("/connections/upstox/exchange-code", payload);
}

export function testUpstoxConnection() {
  return axiosClient.post("/connections/upstox/test");
}

export function disconnectUpstoxConnection() {
  return axiosClient.delete("/connections/upstox");
}

export function saveTelegramConnection(payload) {
  return axiosClient.post("/connections/telegram", payload);
}

export function testTelegramConnection() {
  return axiosClient.post("/connections/telegram/test");
}

export function disconnectTelegramConnection() {
  return axiosClient.delete("/connections/telegram");
}

export function getMyTelegramConnection() {
  return axiosClient.get("/connections/telegram/me");
}

export function startMyTelegramConnection() {
  return axiosClient.post("/connections/telegram/me/start");
}

export function verifyMyTelegramConnection() {
  return axiosClient.post("/connections/telegram/me/verify");
}

export function testMyTelegramConnection() {
  return axiosClient.post("/connections/telegram/me/test");
}