/**
 * API utility functions for communicating with the Flask backend.
 * Handles authentication, requests, and error handling.
 */

import axios from "axios";

/* ---------------------------------------------
   Base URL normalization
   Put ONLY the origin in REACT_APP_API_BASE / REACT_APP_API_URL.
   We will append "/api" exactly once.
---------------------------------------------- */
const RAW_ENV =
  process.env.REACT_APP_API_BASE ||
  process.env.REACT_APP_API_URL ||
  "http://localhost:5000";

// 1) trim trailing slashes
// 2) strip a trailing "/api" if someone included it in the env by mistake
const BASE = RAW_ENV.replace(/\/+$/, "").replace(/\/api\/?$/i, "");

// Axios instance (server mounts all endpoints under /api)
const api = axios.create({
  baseURL: `${BASE}/api`,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
  withCredentials: false, // we use Bearer tokens, not cookies
});

/* ---------------------------------------------
   Token & User helpers (localStorage)
---------------------------------------------- */
const TOKEN_KEY = "token";
const USER_KEY = "user";

export const setAuthToken = (token) =>
  token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY);

export const getAuthToken = () => localStorage.getItem(TOKEN_KEY) || null;

export const setUser = (user) =>
  user ? localStorage.setItem(USER_KEY, JSON.stringify(user)) : localStorage.removeItem(USER_KEY);

export const getUser = () => {
  const raw = localStorage.getItem(USER_KEY);
  try {
    return raw ? JSON.parse(raw) : null;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
};

export const logout = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  if (window.location.pathname !== "/login") window.location.href = "/login";
};

/* ---------------------------------------------
   Interceptors
---------------------------------------------- */
api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error?.response?.status === 401) logout();
    return Promise.reject(error);
  }
);

/* ---------------------------------------------
   Error normalization
---------------------------------------------- */
export const handleApiError = (error) => {
  if (error?.response?.data?.error) return error.response.data.error;
  if (error?.response?.data?.message) return error.response.data.message;
  if (error?.message) return error.message;
  return "An unexpected error occurred";
};

/* ---------------------------------------------
   AUTH
---------------------------------------------- */
export const authAPI = {
  login: async (credentials) => {
    const { data } = await api.post("/auth/login", credentials);
    if (data?.access_token) setAuthToken(data.access_token);
    if (data?.user) setUser(data.user);
    return data;
  },

  signup: async (userData) => {
    const { data } = await api.post("/auth/signup", userData);
    if (data?.access_token) setAuthToken(data.access_token);
    if (data?.user) setUser(data.user);
    return data;
  },

  verifyToken: async () => {
    const { data } = await api.get("/auth/verify");
    return data;
  },

  getProfile: async () => {
    const { data } = await api.get("/auth/profile");
    return data;
  },
};

/* ---------------------------------------------
   TASKS
---------------------------------------------- */
export const taskAPI = {
  getTasks: async (filters = {}) => {
    const params = new URLSearchParams(filters);
    const qs = params.toString();
    const url = qs ? `/tasks?${qs}` : "/tasks";
    const { data } = await api.get(url);
    return data;
  },

  getTask: async (taskId) => {
    const { data } = await api.get(`/tasks/${taskId}`);
    return data;
  },

  createTask: async (taskData) => {
    const { data } = await api.post("/tasks", taskData);
    return data;
  },

  updateTask: async (taskId, taskData) => {
    const { data } = await api.put(`/tasks/${taskId}`, taskData);
    return data;
  },

  deleteTask: async (taskId) => {
    const { data } = await api.delete(`/tasks/${taskId}`);
    return data;
  },

  getStats: async () => {
    const { data } = await api.get("/tasks/stats");
    return data;
  },
};

/* ---------------------------------------------
   AI
---------------------------------------------- */
export const aiAPI = {
  parseTask: async (input) => {
    const { data } = await api.post("/ai/parse-task", { input });
    return data;
  },

  createFromText: async (input) => {
    const { data } = await api.post("/ai/create-from-text", { input });
    return data;
  },

  prioritizeTasks: async (taskIds = null) => {
    const payload = taskIds ? { task_ids: taskIds } : {};
    const { data } = await api.post("/ai/prioritize-tasks", payload);
    return data;
  },

  generateSummary: async (period = "daily") => {
    const { data } = await api.get("/ai/generate-summary", { params: { period } });
    return data;
  },

  suggestSubtasks: async (title, description = "") => {
    const { data } = await api.post("/ai/suggest-subtasks", { title, description });
    return data;
  },

  healthCheck: async () => {
    const { data } = await api.get("/ai/health");
    return data;
  },
};

export default api;
