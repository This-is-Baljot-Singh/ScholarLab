// ScholarLab/frontend/src/api/client.ts
import axios, { AxiosError } from 'axios';
import type {
  AxiosInstance,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from 'axios';
import { useAuthStore } from '../store/authStore';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, API_BASE_URL } from '../constants/auth';

interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

class ApiClient {
  private axiosInstance: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    onSuccess: (token: string) => void;
    onFailed: (error: AxiosError) => void;
  }> = [];

  constructor() {
    this.axiosInstance = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.axiosInstance.interceptors.request.use(
      (config: CustomAxiosRequestConfig) => {
        const token = localStorage.getItem(ACCESS_TOKEN_KEY);
        // Guard against stringified "undefined" or "null" saving errors
        if (token && token !== 'undefined' && token !== 'null') {
          config.headers.set('Authorization', `Bearer ${token}`);
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    this.axiosInstance.interceptors.response.use(
      (response: AxiosResponse) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as CustomAxiosRequestConfig;

        // Don't retry if no response or not a 401
        if (!error.response || error.response.status !== 401 || !originalRequest) {
          return Promise.reject(error);
        }

        // Don't retry refresh token requests
        if (originalRequest.url?.includes('/token/refresh')) {
          this.handleLogout();
          return Promise.reject(error);
        }

        // Prevent infinite retry loops
        if (originalRequest._retry) {
          this.handleLogout();
          return Promise.reject(error);
        }

        originalRequest._retry = true;

        if (this.isRefreshing) {
          return new Promise((resolve, reject) => {
            this.failedQueue.push({
              onSuccess: (token: string) => {
                originalRequest.headers.set('Authorization', `Bearer ${token}`);
                resolve(this.axiosInstance(originalRequest));
              },
              onFailed: (err: AxiosError) => {
                reject(err);
              },
            });
          });
        }

        this.isRefreshing = true;

        try {
          const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
          if (!refreshToken || refreshToken === 'undefined') {
            throw new Error('No valid refresh token available');
          }

          const response = await this.axiosInstance.post('/auth/token/refresh', {
            refresh_token: refreshToken,
          });

          // CRITICAL FIX: Destructure the snake_case keys that FastAPI returns
          const { access_token, refresh_token: new_refresh_token } = response.data;
          
          localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
          if (new_refresh_token) {
            localStorage.setItem(REFRESH_TOKEN_KEY, new_refresh_token);
          }

          const authStore = useAuthStore.getState();
          authStore.refreshAccessToken(access_token);

          originalRequest.headers.set('Authorization', `Bearer ${access_token}`);

          this.processQueue(null, access_token);
          return this.axiosInstance(originalRequest);
        } catch (err) {
          this.processQueue(err as AxiosError);
          this.handleLogout();
          return Promise.reject(err);
        } finally {
          this.isRefreshing = false;
        }
      }
    );
  }

  private processQueue(
    error: AxiosError | null,
    token?: string
  ) {
    this.failedQueue.forEach((item) => {
      if (error) {
        item.onFailed(error);
      } else if (token) {
        item.onSuccess(token);
      }
    });

    this.failedQueue = [];
  }

  private handleLogout() {
    const authStore = useAuthStore.getState();
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    authStore.logout();
    window.location.href = '/login';
  }

  public getInstance(): AxiosInstance {
    return this.axiosInstance;
  }

  public get<T = any>(url: string, config?: any) {
    return this.axiosInstance.get<T>(url, config);
  }

  public post<T = any>(url: string, data?: any, config?: any) {
    return this.axiosInstance.post<T>(url, data, config);
  }

  public put<T = any>(url: string, data?: any, config?: any) {
    return this.axiosInstance.put<T>(url, data, config);
  }

  public patch<T = any>(url: string, data?: any, config?: any) {
    return this.axiosInstance.patch<T>(url, data, config);
  }

  public delete<T = any>(url: string, config?: any) {
    return this.axiosInstance.delete<T>(url, config);
  }
}

export const apiClient = new ApiClient();
export const axiosInstance = apiClient.getInstance();