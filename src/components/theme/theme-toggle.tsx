import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

type Theme = 'light' | 'dark';

function getInitialTheme(): Theme {
  // The inline script in index.html has already applied the correct class
  // before paint; read back from it so this component is in sync.
  if (typeof document !== 'undefined' && document.documentElement.classList.contains('dark')) {
    return 'dark';
  }
  return 'light';
}

const THEME_EVENT = 'app:theme-change';

function hasSavedTheme(): boolean {
  try {
    return localStorage.getItem('theme') !== null;
  } catch {
    return false;
  }
}

/** Apply a theme to <html>. Only an explicit user choice is persisted. */
function applyTheme(theme: Theme, persist: boolean) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  // Keeps the mobile browser chrome in step with the page.
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', theme === 'dark' ? '#07111a' : '#0d9488');
  if (persist) {
    try {
      localStorage.setItem('theme', theme);
    } catch {
      // localStorage can throw in private mode / blocked storage — ignore.
    }
  }
  // Several toggles can be mounted at once (public header + app header);
  // tell the others so their icons do not go stale.
  window.dispatchEvent(new CustomEvent<Theme>(THEME_EVENT, { detail: theme }));
}

/** Light/dark theme switch. Persists the choice and keeps <html> in sync. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    const onThemeEvent = (e: Event) => setTheme((e as CustomEvent<Theme>).detail);
    window.addEventListener(THEME_EVENT, onThemeEvent);

    // Until the user picks a theme themselves, follow the OS setting live.
    // (Previously the first render wrote the detected theme to localStorage,
    // which silently pinned it and ignored later OS changes.)
    const media = window.matchMedia?.('(prefers-color-scheme: dark)');
    const onSystemChange = (e: MediaQueryListEvent) => {
      if (!hasSavedTheme()) applyTheme(e.matches ? 'dark' : 'light', false);
    };
    media?.addEventListener?.('change', onSystemChange);

    // Another tab changed the theme.
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'theme' && (e.newValue === 'dark' || e.newValue === 'light')) {
        applyTheme(e.newValue, false);
      }
    };
    window.addEventListener('storage', onStorage);

    return () => {
      window.removeEventListener(THEME_EVENT, onThemeEvent);
      media?.removeEventListener?.('change', onSystemChange);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  const isDark = theme === 'dark';
  const next: Theme = isDark ? 'light' : 'dark';

  return (
    <button
      type="button"
      onClick={() => applyTheme(next, true)}
      className="p-2 rounded-full text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors"
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    >
      {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
    </button>
  );
}
