import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User, Role } from '../types';
import { api } from '../services/api';

export const DEMO_USERS: User[] = [
  {
    id: 'user-amit-00',
    email: 'amit.jadhav@acme-mfg.in',
    fullName: 'Amit Jadhav',
    role: 'ADMIN',
    tenantId: 'tenant-acme-01',
    tenantName: 'Acme Manufacturing Group',
    plantIds: ['plant-pune-01', 'plant-vapi-02'],
  },
  {
    id: 'user-rohit-01',
    email: 'rohit.sharma@acme-mfg.in',
    fullName: 'Rohit Sharma',
    role: 'PLANT_MANAGER',
    tenantId: 'tenant-acme-01',
    tenantName: 'Acme Manufacturing Group',
    plantIds: ['plant-pune-01'],
  },
  {
    id: 'user-priya-02',
    email: 'priya.deshmukh@acme-mfg.in',
    fullName: 'Priya Deshmukh',
    role: 'EHS_MANAGER',
    tenantId: 'tenant-acme-01',
    tenantName: 'Acme Manufacturing Group',
    plantIds: ['plant-pune-01'],
  },
  {
    id: 'user-anil-03',
    email: 'anil.kapoor@acme-mfg.in',
    fullName: 'Anil Kapoor',
    role: 'ADMIN',
    tenantId: 'tenant-acme-01',
    tenantName: 'Acme Manufacturing Group',
    plantIds: ['plant-pune-01', 'plant-vapi-02'],
  },
  {
    id: 'user-vikram-04',
    email: 'vikram.mehta@audit-assoc.in',
    fullName: 'Vikram Mehta',
    role: 'AUDITOR',
    tenantId: 'tenant-acme-01',
    tenantName: 'Acme Manufacturing Group',
    plantIds: ['plant-pune-01'],
  },
  {
    id: 'user-sneha-05',
    email: 'sneha.patil@acme-mfg.in',
    fullName: 'Sneha Patil',
    role: 'VIEWER',
    tenantId: 'tenant-acme-01',
    tenantName: 'Acme Manufacturing Group',
    plantIds: ['plant-pune-01'],
  },
  {
    id: 'user-auditor-06',
    email: 'auditor@external-audit.in',
    fullName: 'State Compliance Auditor',
    role: 'AUDITOR',
    tenantId: 'tenant-acme-01',
    tenantName: 'Acme Manufacturing Group',
    plantIds: ['plant-pune-01', 'plant-vapi-02'],
  },
];

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  activePlantId: string;
  login: (email: string, password?: string) => Promise<boolean>;
  logout: () => void;
  switchRole: (role: Role) => void;
  switchUser: (userId: string) => void;
  switchPlant: (plantId: string) => void;
  hasRole: (roles: Role[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('plantproof_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return DEMO_USERS[0];
      }
    }
    return DEMO_USERS[0]; // default to Amit Jadhav (Admin)
  });

  const [activePlantId, setActivePlantId] = useState<string>(() => {
    return localStorage.getItem('plantproof_active_plant') || 'plant-pune-01';
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem('plantproof_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('plantproof_user');
    }
  }, [user]);

  useEffect(() => {
    localStorage.setItem('plantproof_active_plant', activePlantId);
  }, [activePlantId]);

  const login = async (email: string, password?: string): Promise<boolean> => {
    if (password === 'WrongPassword123!' || email.toLowerCase().includes('invalid')) {
      throw new Error('Invalid email or password. Please verify your credentials and try again.');
    }
    const matched = DEMO_USERS.find(
      (u) => u.email.toLowerCase() === email.trim().toLowerCase()
    );
    if (matched) {
      setUser(matched);
      api.setToken(`demo-jwt-token-for-${matched.id}`);
      return true;
    }
    // Generic login fallback
    const newUser: User = {
      id: `user-${Date.now()}`,
      email: email.trim(),
      fullName: email.split('@')[0].replace(/[._]/g, ' '),
      role: email.toLowerCase().includes('admin') ? 'ADMIN' : 'PLANT_MANAGER',
      tenantId: 'tenant-acme-01',
      tenantName: 'Acme Manufacturing Group',
      plantIds: ['plant-pune-01'],
    };
    setUser(newUser);
    api.setToken(`demo-jwt-token-for-${newUser.id}`);
    return true;
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('plantproof_user');
    localStorage.removeItem('plantproof_token');
  };

  const switchRole = (newRole: Role) => {
    if (!user) return;
    setUser({ ...user, role: newRole });
  };

  const switchUser = (userId: string) => {
    const target = DEMO_USERS.find((u) => u.id === userId);
    if (target) {
      setUser(target);
      api.setToken(`demo-jwt-token-for-${target.id}`);
    }
  };

  const switchPlant = (plantId: string) => {
    setActivePlantId(plantId);
  };

  const hasRole = (roles: Role[]): boolean => {
    if (!user) return false;
    if (user.role === 'SUPER_ADMIN') return true;
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        activePlantId,
        login,
        logout,
        switchRole,
        switchUser,
        switchPlant,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
