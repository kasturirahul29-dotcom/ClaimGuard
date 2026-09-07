import { useMemo } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

export function useApi() {
  const { tokens, login, logout } = useAuth();

  const api = useMemo(() => {
    const instance = axios.create({
      baseURL: 'http://localhost:8000/api/v1/',
    });

    // Attach access token to every request
    instance.interceptors.request.use(config => {
      if (tokens?.access) {
        config.headers.Authorization = `Bearer ${tokens.access}`;
      }
      return config;
    });

    // Intercept 401s and attempt to refresh the token
    instance.interceptors.response.use(
      response => response,
      async error => {
        const originalRequest = error.config;
        
        // Prevent infinite loops with _retry flag
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          if (tokens?.refresh) {
            try {
              const res = await axios.post('http://localhost:8000/api/v1/auth/refresh/', {
                refresh: tokens.refresh
              });
              
              const newAccess = res.data.access;
              // Update context state
              login({ access: newAccess, refresh: tokens.refresh });
              
              // Retry the original request with the new token
              originalRequest.headers.Authorization = `Bearer ${newAccess}`;
              return instance(originalRequest);
            } catch (err) {
              // Refresh token is invalid/expired
              logout();
            }
          } else {
            logout();
          }
        }
        return Promise.reject(error);
      }
    );

    return instance;
  }, [tokens, login, logout]);

  return api;
}
