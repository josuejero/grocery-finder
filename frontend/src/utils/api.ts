// frontend/src/utils/api.ts

import axios from "axios";

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth-token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("auth-token");
      window.location.href = "/auth/login";
    }
    return Promise.reject(error);
  }
);

export default apiClient;