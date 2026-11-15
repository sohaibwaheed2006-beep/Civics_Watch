import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, LoginCredentials, RegisterData } from '@/types/auth';
import { authService } from '@/services/auth-service';
import { authStorage } from '@/lib/api-client';
import { queryClient } from '@/lib/query-client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /**
   * True only once the backend has confirmed the session (login, or a
   * successful /auth/me). A user restored from localStorage is NOT verified
   * until then. Public pages use this so they never greet a visitor with a
   * stale or expired account.
   */
  sessionVerified: boolean;
  login: (credentials: LoginCredentials) => Promise<User>;
  register: (data: RegisterData) => Promise<User>;
  logout: () => Promise<void>;
  updateCurrentUserState: (user: User) => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => authStorage.getUser<User>());
  const [token, setToken] = useState<string | null>(() => authStorage.getToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [sessionVerified, setSessionVerified] = useState<boolean>(false);

  const refreshUser = useCallback(async () => {
    try {
      const currentToken = authStorage.getToken();
      if (!currentToken) {
        authStorage.clear();
        setUser(null);
        setToken(null);
        setSessionVerified(false);
        return;
      }
      try {
        const currentUser = await authService.fetchCurrentUser();
        setUser(currentUser);
        setToken(currentToken);
        setSessionVerified(true);
      } catch (error) {
        const status = (error as { response?: { status?: number } })?.response?.status;
        const storedUser = authStorage.getUser<User>();
        if (status === undefined && storedUser) {
          // Server unreachable (asleep / offline): keep the remembered
          // session for protected pages, but it stays unverified.
          setUser(storedUser);
          setToken(currentToken);
          setSessionVerified(false);
        } else {
          authStorage.clear();
          setUser(null);
          setToken(null);
          setSessionVerified(false);
        }
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (credentials: LoginCredentials): Promise<User> => {
    setIsLoading(true);
    try {
      const res = await authService.login(credentials);
      setUser(res.user);
      setToken(res.accessToken);
      setSessionVerified(true);
      // Invalidate existing queries
      queryClient.clear();
      return res.user;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterData): Promise<User> => {
    // Registration creates the account but does NOT start a session. The user
    // is directed to the sign-in page to log in explicitly afterwards, so we
    // do not set the user/token here.
    return await authService.register(data);
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setToken(null);
      setSessionVerified(false);
      queryClient.clear();
      setIsLoading(false);
    }
  };

  const updateCurrentUserState = (updatedUser: User) => {
    setUser(updatedUser);
    authStorage.setUser(updatedUser);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: Boolean(user && token),
        isLoading,
        sessionVerified,
        login,
        register,
        logout,
        updateCurrentUserState,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
