/**
 * API utility functions for communicating with Flask backend.
 * Handles authentication, requests, and error handling.
 */

import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    console.log('API Request interceptor - URL:', config.url);
    console.log('API Request interceptor - token:', token ? `exists (${token.substring(0, 20)}...)` : 'missing');
    console.log('API Request interceptor - localStorage contents:', Object.keys(localStorage));

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('Added Authorization header to request');
    } else {
      console.log('No token found in localStorage - request will be unauthorized');
    }
    return config;
  },
  (error) => {
    console.error('API Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => {
    console.log('API Response interceptor - Success:', response.config.url, response.status);
    return response;
  },
  (error) => {
    console.log('API Response interceptor - Error:', error.config?.url, error.response?.status, error.message);
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API functions
export const authAPI = {
  login: async (credentials) => {
    const response = await api.post('/auth/login', credentials);
    return response.data;
  },

  signup: async (userData) => {
    const response = await api.post('/auth/signup', userData);
    return response.data;
  },

  verifyToken: async () => {
    const response = await api.get('/auth/verify');
    return response.data;
  },

  getProfile: async () => {
    const response = await api.get('/auth/profile');
    return response.data;
  },
};

// Task API functions
export const taskAPI = {
  getTasks: async (filters = {}) => {
    const params = new URLSearchParams(filters);
    const queryString = params.toString();
    const url = queryString ? `/tasks?${queryString}` : '/tasks';
    const response = await api.get(url);
    return response.data;
  },

  getTask: async (taskId) => {
    const response = await api.get(`/tasks/${taskId}`);
    return response.data;
  },

  createTask: async (taskData) => {
    const response = await api.post('/tasks', taskData);
    return response.data;
  },

  updateTask: async (taskId, taskData) => {
    const response = await api.put(`/tasks/${taskId}`, taskData);
    return response.data;
  },

  deleteTask: async (taskId) => {
    const response = await api.delete(`/tasks/${taskId}`);
    return response.data;
  },

  getStats: async () => {
    const response = await api.get('/tasks/stats');
    return response.data;
  },
};

// AI API functions
export const aiAPI = {
  parseTask: async (input) => {
    const response = await api.post('/ai/parse-task', { input });
    return response.data;
  },

  createFromText: async (input) => {
    const response = await api.post('/ai/create-from-text', { input });
    return response.data;
  },

  prioritizeTasks: async (taskIds = null) => {
    const payload = taskIds ? { task_ids: taskIds } : {};
    const response = await api.post('/ai/prioritize-tasks', payload);
    return response.data;
  },

  generateSummary: async (period = 'daily') => {
    const response = await api.get(`/ai/generate-summary?period=${period}`);
    return response.data;
  },

  suggestSubtasks: async (title, description = '') => {
    const response = await api.post('/ai/suggest-subtasks', { title, description });
    return response.data;
  },

  healthCheck: async () => {
    const response = await api.get('/ai/health');
    return response.data;
  },
};

// Utility functions
export const setAuthToken = (token) => {
  console.log('setAuthToken called with:', token ? 'token provided' : 'null/undefined');
  if (token) {
    localStorage.setItem('token', token);
    console.log('Token stored in localStorage');
    // Verify it was stored
    const stored = localStorage.getItem('token');
    console.log('Verification - token in localStorage:', stored ? 'exists' : 'missing');
  } else {
    localStorage.removeItem('token');
    console.log('Token removed from localStorage');
  }
};

export const getAuthToken = () => {
  return localStorage.getItem('token');
};

export const setUser = (user) => {
  if (user) {
    localStorage.setItem('user', JSON.stringify(user));
  } else {
    localStorage.removeItem('user');
  }
};

export const getUser = () => {
  const user = localStorage.getItem('user');
  return user ? JSON.parse(user) : null;
};

export const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = '/login';
};

// Error handling utility
export const handleApiError = (error) => {
  if (error.response?.data?.error) {
    return error.response.data.error;
  } else if (error.message) {
    return error.message;
  } else {
    return 'An unexpected error occurred';
  }
};

export default api;
