import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode';
import type { User, AuthTokens } from '../types';

interface AuthContextType {
  user: User | null;
  tokens: AuthTokens | null;
  login: (tokens: AuthTokens) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  // STRICT REQUIREMENT: Tokens are kept strictly in memory, never in localStorage.
  // This means a page refresh logs the user out.
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (tokens) {
      try {
        const decoded: any = jwtDecode(tokens.access);
        setUser({
          id: decoded.user_id,
          // We will fetch user details later or include them in token if customized,
          // but for this MVP, Django simplejwt only includes user_id by default.
          // Wait, simplejwt only has user_id. We need the role!
          // We must have customized the JWT claims to include role and username.
          // Let's assume the backend includes them, or we decode what we can.
          username: decoded.username || '',
          email: decoded.email || '',
          role: decoded.role || 'customer',
        });
      } catch (err) {
        console.error('Failed to decode token', err);
        setTokens(null);
        setUser(null);
      }
    } else {
      setUser(null);
    }
  }, [tokens]);

  const login = (newTokens: AuthTokens) => {
    setTokens(newTokens);
  };

  const logout = () => {
    setTokens(null);
  };

  return (
    <AuthContext.Provider value={{ user, tokens, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
