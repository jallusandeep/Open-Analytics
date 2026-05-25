import axiosClient from "./axiosClient";

export function getConnections() {
  return axiosClient.get("/connections");
}

export function saveUpstoxConnection(payload) {
  return axiosClient.post("/connections/upstox", payload);
}

export function testUpstoxConnection() {
  return axiosClient.post("/connections/upstox/test");
}

export function disconnectUpstoxConnection() {
  return axiosClient.delete("/connections/upstox");
}