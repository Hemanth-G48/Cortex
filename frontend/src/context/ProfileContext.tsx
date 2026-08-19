import { createContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { profileApi, type User } from '../services/api';

interface ProfileState {
  profile: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

const ProfileContext = createContext<ProfileState>({
  profile: null,
  loading: true,
  refresh: async () => {},
});

/**
 * Single-owner profile provider.
 *
 * The application is a local, single-user app: there is exactly one owner and
 * no login. This provider loads the owner's profile once and exposes it to
 * the whole tree, replacing the old multi-user AuthContext.
 */
export const ProfileProvider = ({ children }: { children: ReactNode }) => {
  const [profile, setProfile] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const r = await profileApi.get();
      setProfile(r.user);
    } catch {
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <ProfileContext.Provider value={{ profile, loading, refresh }}>
      {children}
    </ProfileContext.Provider>
  );
};

export default ProfileContext;
