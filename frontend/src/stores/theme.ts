import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ThemeState {
  dark: boolean;
  toggle: () => void;
  setDark: (v: boolean) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      dark: false,
      toggle: () => {
        const next = !get().dark;
        document.documentElement.classList.toggle("dark", next);
        set({ dark: next });
      },
      setDark: (v) => {
        document.documentElement.classList.toggle("dark", v);
        set({ dark: v });
      },
    }),
    { name: "autoclaim-theme" }
  )
);
