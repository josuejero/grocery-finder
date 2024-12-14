import axios from "axios";

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
  timeout: 5000,
});

apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem("auth-storage-token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export async function fetcher<T>(url: string): Promise<T> {
  const response = await apiClient.get(url);
  return response.data;
}

export default apiClient;
