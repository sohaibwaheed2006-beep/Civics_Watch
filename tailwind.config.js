/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Inter is loaded in index.html but was never wired into Tailwind, so
        // the app fell back to the system font. Make Inter the default sans
        // stack (with graceful system fallbacks) so typography is consistent.
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
      colors: {
        brand: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
        },
      },
      // Slate-tinted, multi-layer elevation. Pure-black shadows read muddy on
      // the cool slate canvas; tinting them with slate (15 23 42) and keeping
      // them soft gives surfaces a lighter, more premium lift.
      boxShadow: {
        xs: '0 1px 2px 0 rgb(15 23 42 / 0.04)',
        sm: '0 1px 2px 0 rgb(15 23 42 / 0.05), 0 1px 3px -1px rgb(15 23 42 / 0.04)',
        DEFAULT: '0 1px 3px 0 rgb(15 23 42 / 0.06), 0 1px 2px -1px rgb(15 23 42 / 0.05)',
        md: '0 4px 6px -2px rgb(15 23 42 / 0.06), 0 2px 4px -2px rgb(15 23 42 / 0.05)',
        lg: '0 12px 20px -6px rgb(15 23 42 / 0.10), 0 4px 8px -4px rgb(15 23 42 / 0.06)',
        xl: '0 20px 32px -8px rgb(15 23 42 / 0.14), 0 8px 12px -6px rgb(15 23 42 / 0.08)',
        '2xl': '0 32px 56px -12px rgb(15 23 42 / 0.22)',
      },
      // Composable enter animations (dropdowns, popovers, toasts). These stand
      // in for `tailwindcss-animate`, which the project does not install; the
      // utilities that drive them live in src/styles/index.css.
      keyframes: {
        'enter': {
          from: {
            opacity: 'var(--tw-enter-opacity, 1)',
            transform:
              'translate3d(var(--tw-enter-translate-x, 0), var(--tw-enter-translate-y, 0), 0) scale(var(--tw-enter-scale, 1))',
          },
        },
      },
      animation: {
        enter: 'enter 160ms cubic-bezier(0.16, 1, 0.3, 1) both',
      },
    },
  },
  plugins: [],
}
