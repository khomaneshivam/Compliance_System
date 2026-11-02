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
  isLoading: boolean;
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
    // Demo identities are a development-only preview feature. Production must
    // begin unauthenticated and restore identity from the signed backend token.
    if (!import.meta.env.DEV) return null;
    const saved = localStorage.getItem('plantproof_user');
    if (saved) {
      try {
        return JSON.parse(saved) as User;
      } catch {
        localStorage.removeItem('plantproof_user');
      }
    }
    return DEMO_USERS[0];
  });
  const [isLoading, setIsLoading] = useState<boolean>(() => !import.meta.env.DEV && !!api.getToken());

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
    const token = api.getToken();
    if (!token) {
      setIsLoading(false);
      return;
    }
    if (import.meta.env.DEV && token.startsWith('demo-jwt-token-for-')) {
      setIsLoading(false);
      return;
    }

    let active = true;
    setIsLoading(true);
    api.getCurrentUser()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch(() => {
        if (active) {
          api.setToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    localStorage.setItem('plantproof_active_plant', activePlantId);
  }, [activePlantId]);

  const login = async (email: string, password?: string): Promise<boolean> => {
    if (!password) throw new Error('Password is required.');
    const authenticated = await api.login(email, password);
    setUser(authenticated.user);
    setActivePlantId(authenticated.user.plantIds[0] || '');
    return true;
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('plantproof_user');
    api.setToken(null);
    localStorage.removeItem('plantproof_token');
  };

  const switchRole = (newRole: Role) => {
    if (!import.meta.env.DEV || !user) return;
    setUser({ ...user, role: newRole });
  };

  const switchUser = (userId: string) => {
    if (!import.meta.env.DEV) return;
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
        isLoading,
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
