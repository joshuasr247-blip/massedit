import { create } from 'zustand';
import { supabase } from '../lib/supabase';

export const useAuthStore = create((set, get) => ({
  user: null,
  session: null,
  loading: true,
  error: null,

  // Initialize auth â call once on app mount
  init: async () => {
    try {
      // Get current session
      const { data: { session }, error } = await supabase.auth.getSession();
      if (error) throw error;

      set({
        session,
        user: session?.user ?? null,
        loading: false,
      });

      // Listen for auth changes (login, logout, token refresh)
      supabase.auth.onAuthStateChange((_event, session) => {
        set({
          session,
          user: session?.user ?? null,
        });
      });
    } catch (error) {
      console.error('Auth init error:', error);
      set({ loading: false, error: error.message });
    }
  },

  // Sign up with email + password
  signUp: async (email, password) => {
    set({ error: null, loading: true });
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
      });
      if (error) throw error;
      set({ loading: false });
      return data;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  // Sign in with email + password
  signIn: async (email, password) => {
    set({ error: null, loading: true });
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) throw error;
      set({ loading: false });
      return data;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  // Sign out
  signOut: async () => {
    set({ error: null });
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      set({ user: null, session: null });
    } catch (error) {
      set({ error: error.message });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));
