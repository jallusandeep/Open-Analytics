import axiosClient from "./axiosClient";

export function getAutomatedStockPredictions() {
  return axiosClient.get("/quant-research/predictions/auto", {
    params: { limit: 1000, rebuild: false }
  });
}

export function getQuantResearchReadiness() {
  return axiosClient.get("/quant-research/readiness");
}

export function getQuantPipelineStatus() {
  return axiosClient.get("/quant-research/pipeline/status");
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

export function buildQuantRisk() {
  return axiosClient.post("/quant-research/risk/build");
}

export function buildQuantTradePlans() {
  return axiosClient.post("/quant-research/trade-plans/build");
}

export function buildQuantMlDataset() {
  return axiosClient.post("/quant-research/ml/datasets/build");
}

export function trainQuantMlModel() {
  return axiosClient.post("/quant-research/ml/models/train");
}

export function getQuantMlDatasets() {
  return axiosClient.get("/quant-research/ml/datasets");
}

export function getQuantMlModels() {
  return axiosClient.get("/quant-research/ml/models");
}

export function buildQuantDeepLearningDataset() {
  return axiosClient.post("/quant-research/deep-learning/datasets/build");
}

export function trainQuantDeepLearningModel() {
  return axiosClient.post("/quant-research/deep-learning/models/train");
}

export function getQuantDeepLearningDatasets() {
  return axiosClient.get("/quant-research/deep-learning/datasets");
}

export function getQuantDeepLearningModels() {
  return axiosClient.get("/quant-research/deep-learning/models");
}

