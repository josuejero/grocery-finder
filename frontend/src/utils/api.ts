import axios from "axios";

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor with detailed logging
apiClient.interceptors.request.use((config) => {
  console.log('🚀 Request Config:', {
    url: config.url,
    method: config.method,
    headers: config.headers
  });
  
  const token = localStorage.getItem("auth-token");
  if (token && config.headers) {
    // Changed this part to properly set the Authorization header
    config.headers.Authorization = `Bearer ${token}`;
    console.log('🔑 Token added to request');
  } else {
    console.warn('⚠️ No auth token found in localStorage');
  }
  return config;
}, (error) => {
  console.error('❌ Request interceptor error:', error);
  return Promise.reject(error);
});

// Response interceptor with enhanced error handling
apiClient.interceptors.response.use(
  (response) => {
    console.log('✅ Response:', {
      url: response.config.url,
      status: response.status,
      data: response.data,
      headers: response.headers
    });
    return response;
  },
  (error) => {
    console.error('❌ Response error details:', {
      url: error.config?.url,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      headers: error.response?.headers,
      requestHeaders: error.config?.headers
    });

    if (error.response?.status === 401) {
      localStorage.removeItem("auth-token");
      window.location.href = "/auth/login";
    }
    return Promise.reject(error);
  }
);

export async function fetcher<T>(url: string): Promise<T> {
  try {
    console.log('📡 Fetching:', url);
    const response = await apiClient.get(url);
    return response.data;
  } catch (error) {
    console.error('❌ Fetch error:', error);
    throw error;
  }
}

export default apiClient;