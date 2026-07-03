import axiosClient from "./axiosClient";

export function getQuantResearchReadiness() {
  return axiosClient.get("/quant-research/readiness");
}

export function buildQuantFeatures() {
  return axiosClient.post("/quant-research/features/build");
}

export function buildQuantLabels() {
  return axiosClient.post("/quant-research/labels/build");
}

export function discoverQuantPatterns() {
  return axiosClient.post("/quant-research/patterns/discover");
}

export function runQuantBacktest() {
  return axiosClient.post("/quant-research/backtests/run");
}

export function buildQuantRankings() {
  return axiosClient.post("/quant-research/rankings/build");
}
