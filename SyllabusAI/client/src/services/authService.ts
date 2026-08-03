import api from './api';
import { signInWithPopup } from 'firebase/auth';
import { auth, googleProvider } from '../config/firebase';

export interface User {
  id: number;
  email: string;
  firstName: string;
  lastName: string;
  role: 'user' | 'admin';
  institutionId?: number | null;
  courseId?: number | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  institution?: { id: number; name: string; shortName: string } | null;
  course?: { id: number; name: string; code: string; duration: number } | null;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  institutionId?: number;
  courseId?: number;
}

export interface AuthResponse {
  message: string;
  user: User;
  token: string;
}

export const authService = {
  async login(data: LoginData): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/login', data);
    return response.data;
  },

  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/register', data);
    return response.data;
  },

  async googleSignIn(): Promise<AuthResponse> {
    const result = await signInWithPopup(auth, googleProvider);
    const idToken = await result.user.getIdToken();
    const response = await api.post<AuthResponse>('/auth/google', { idToken });
    return response.data;
  },

  async completeProfile(data: { firstName?: string; lastName?: string; institutionId: number; courseId: number }): Promise<{ message: string; user: User }> {
    const response = await api.put<{ message: string; user: User }>('/auth/complete-profile', data);
    return response.data;
  },

  async getProfile(): Promise<{ user: User }> {
    const response = await api.get<{ user: User }>('/auth/profile');
    return response.data;
  },

  async updateProfile(data: { firstName: string; lastName: string }): Promise<{ message: string; user: User }> {
    const response = await api.put<{ message: string; user: User }>('/auth/profile', data);
    return response.data;
  },

  async changePassword(data: { currentPassword: string; newPassword: string }): Promise<{ message: string }> {
    const response = await api.put<{ message: string }>('/auth/change-password', data);
    return response.data;
  },

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  },

  getToken(): string | null {
    return localStorage.getItem('token');
  },

  getUser(): User | null {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  },

  setAuthData(token: string, user: User): void {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
  },

  isAuthenticated(): boolean {
    return !!this.getToken();
  },
};

export default authService;
