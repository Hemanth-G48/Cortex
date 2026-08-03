import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import authService, { type User } from '../services/authService';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, firstName: string, lastName: string, institutionId?: number, courseId?: number) => Promise<void>;
  googleSignIn: () => Promise<void>;
  updateUser: (user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedUser = authService.getUser();
    if (storedUser && authService.getToken()) {
      setUser(storedUser);
      authService.getProfile()
        .then(({ user }) => {
          setUser(user);
          authService.setAuthData(authService.getToken()!, user);
        })
        .catch(() => {
          authService.logout();
          setUser(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const response = await authService.login({ email, password });
    authService.setAuthData(response.token, response.user);
    setUser(response.user);
  };

  const register = async (
    email: string,
    password: string,
    firstName: string,
    lastName: string,
    institutionId?: number,
    courseId?: number
  ) => {
    const response = await authService.register({
      email,
      password,
      firstName,
      lastName,
      institutionId,
      courseId,
    });
    authService.setAuthData(response.token, response.user);
    setUser(response.user);
  };

  const googleSignIn = async () => {
    const response = await authService.googleSignIn();
    authService.setAuthData(response.token, response.user);
    setUser(response.user);
  };

  const updateUser = (updatedUser: User) => {
    setUser(updatedUser);
    authService.setAuthData(authService.getToken()!, updatedUser);
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        googleSignIn,
        updateUser,
        logout,
      }}
    >
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
