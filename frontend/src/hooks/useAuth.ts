import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { authApi } from '../services/api';
import type { LoginRequest } from '../types/api';
import { toast } from 'sonner';

export function useAuth() {
  const navigate = useNavigate();
  const { user, isAuthenticated, setAuth, clearAuth } = useAuthStore();

  const loginMutation = useMutation({
    mutationFn: (data: LoginRequest) => authApi.loginLdap(data),
    onSuccess: (data) => {
      setAuth(data.user, data.access_token, data.refresh_token);
      toast.success('Logged in successfully');
      navigate('/');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Login failed');
    },
  });

  const logoutMutation = useMutation({
    mutationFn: () => authApi.logout({ refresh_token: useAuthStore.getState().refreshToken! }),
    onSuccess: () => {
      clearAuth();
      toast.success('Logged out successfully');
      navigate('/auth/login');
    },
  });

  return {
    user,
    isAuthenticated,
    login: loginMutation.mutate,
    logout: logoutMutation.mutate,
    isLoggingIn: loginMutation.isPending,
    isLoggingOut: logoutMutation.isPending,
  };
}
