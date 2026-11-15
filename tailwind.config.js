import palette from 'tailwindcss/colors';
import plugin from 'tailwindcss/plugin';

// ---------------------------------------------------------------------------
// Theme-aware accent colours
//
// The neutral (slate) ramp already inverts for dark mode through CSS
// variables. The accent colours did not, so in dark mode every tinted panel
// (`bg-teal-50`, `bg-amber-50`, ...) stayed near-white and every deep accent
// text (`text-teal-800`, `text-rose-900`, ...) stayed near-black on a dark
// card. Rather than adding `dark:` variants to hundreds of class names, the
// two "roles" an accent plays are made variable-driven here:
//
//   tints (steps 50-300)  backgrounds / borders / rings / gradient stops
//   inks  (steps 600-950) text
//
// Light mode resolves each step to its normal Tailwind value, so nothing
// changes there. Dark mode mirrors the step across the ramp (50 -> 950,
// 800 -> 200, ...). Solid fills (`bg-teal-600`, `bg-rose-500`) and light text
// on dark hero panels (`text-teal-100`) are deliberately NOT remapped, so
// buttons and image overlays look the same in both themes.
// ---------------------------------------------------------------------------
const ACCENTS = [
  'teal', 'emerald', 'amber', 'rose', 'indigo',
  'blue', 'sky', 'purple', 'red', 'yellow',
];
const TINT_DARK = { 50: 950, 100: 900, 200: 800, 300: 700 };
const INK_DARK = { 600: 400, 700: 300, 800: 200, 900: 100, 950: 50 };

const toChannels = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return `${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255}`;
};

const scale = (role, color, steps) =>
  Object.fromEntries(
    Object.keys(steps).map((step) => [
      step,
      `rgb(var(--${role}-${color}-${step}) / <alpha-value>)`,
    ])
  );
const forEachAccent = (role, steps) =>
  Object.fromEntries(ACCENTS.map((c) => [c, scale(role, c, steps)]));

const accentTints = forEachAccent('tint', TINT_DARK);
const accentInks = forEachAccent('ink', INK_DARK);

// CSS custom properties for both themes, generated from Tailwind's palette so
// no colour value is typed by hand.
const accentVariables = (dark) => {
  const vars = {};
  for (const color of ACCENTS) {
    for (const [step, mirrored] of Object.entries(TINT_DARK)) {
      vars[`--tint-${color}-${step}`] = toChannels(palette[color][dark ? mirrored : step]);
    }
    for (const [step, mirrored] of Object.entries(INK_DARK)) {
      vars[`--ink-${color}-${step}`] = toChannels(palette[color][dark ? mirrored : step]);
    }
  }
  return vars;
};

// Elevation helpers. `shade(a)` is a shadow layer whose colour and strength
// follow the theme; `buttonShadow` builds the gloss + glow for solid buttons.
const shade = (alpha) =>
  `rgb(var(--shadow-color) / calc(${alpha} * var(--shadow-strength)))`;
const buttonShadow = (rgb, hover) =>
  [
    'inset 0 1px 0 0 rgb(255 255 255 / 0.2)',
    `0 1px 2px 0 ${shade(0.18)}`,
    hover
      ? `0 8px 18px -6px rgb(${rgb} / 0.5)`
      : `0 4px 10px -4px rgb(${rgb} / 0.4)`,
  ].join(', ');

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  // Dark mode is driven by a `dark` class on <html>, toggled by ThemeToggle
  // and set pre-paint by the inline script in index.html.
  darkMode: 'class',
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
        // The neutral ramp is CSS-variable driven so it can invert for dark
        // mode (see src/styles/index.css). Every existing `*-slate-*` utility
        // — text, bg, border, ring, divide — adapts automatically; no per-
        // component `dark:` classes needed.
        slate: {
          50: 'rgb(var(--slate-50) / <alpha-value>)',
          100: 'rgb(var(--slate-100) / <alpha-value>)',
          200: 'rgb(var(--slate-200) / <alpha-value>)',
          300: 'rgb(var(--slate-300) / <alpha-value>)',
          400: 'rgb(var(--slate-400) / <alpha-value>)',
          500: 'rgb(var(--slate-500) / <alpha-value>)',
          600: 'rgb(var(--slate-600) / <alpha-value>)',
          700: 'rgb(var(--slate-700) / <alpha-value>)',
          800: 'rgb(var(--slate-800) / <alpha-value>)',
          900: 'rgb(var(--slate-900) / <alpha-value>)',
          950: 'rgb(var(--slate-950) / <alpha-value>)',
        },
        // Fixed, never-inverting dark ramp for surfaces that are meant to stay
        // dark in BOTH themes: photo/image overlays, map badges, modal scrims,
        // and the auth hero panels. These sit over imagery or act as scrims, so
        // inverting them would put light text on a light wash.
        ink: {
          200: '#e2e8f0',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
      },
      // `bg-white` is the primary surface color across the app (cards, header,
      // popovers). Remap ONLY the background utility to a variable so those
      // surfaces go dark, while `text-white` / `border-white` stay literally
      // white (needed for text on colored buttons and hero panels).
      backgroundColor: {
        white: 'rgb(var(--surface) / <alpha-value>)',
        ...accentTints,
      },
      // Accent tints and inks follow the theme (see the top of this file).
      borderColor: accentTints,
      gradientColorStops: accentTints,
      textColor: accentInks,
      // Focus-ring offset should match the surface behind the control so the
      // halo reads correctly in both themes.
      ringOffsetColor: {
        white: 'rgb(var(--surface) / <alpha-value>)',
      },
      // Slate-tinted, multi-layer elevation. Pure-black shadows read muddy on
      // the cool slate canvas; tinting them with slate (15 23 42) and keeping
      // them soft gives surfaces a lighter, more premium lift.
      //
      // The colour and strength come from CSS variables (src/styles/index.css)
      // so the same utilities stay visible in dark mode: slate-tinted and
      // light on the pale canvas, pure black and ~3x stronger on the dark one.
      boxShadow: {
        xs: `0 1px 2px 0 ${shade(0.05)}`,
        sm: `0 1px 2px 0 ${shade(0.05)}, 0 2px 6px -2px ${shade(0.06)}`,
        DEFAULT: `0 1px 3px 0 ${shade(0.07)}, 0 2px 8px -3px ${shade(0.06)}`,
        md: `0 2px 4px -1px ${shade(0.05)}, 0 8px 16px -6px ${shade(0.09)}`,
        lg: `0 4px 8px -4px ${shade(0.06)}, 0 16px 28px -8px ${shade(0.12)}`,
        xl: `0 8px 12px -6px ${shade(0.08)}, 0 24px 40px -10px ${shade(0.16)}`,
        '2xl': `0 36px 64px -14px ${shade(0.24)}`,
        // Solid buttons: a 1px top gloss, a tight contact shadow and a soft
        // colour-matched glow that widens on hover.
        'btn-primary': buttonShadow('13 148 136', false),
        'btn-primary-hover': buttonShadow('13 148 136', true),
        'btn-danger': buttonShadow('225 29 72', false),
        'btn-danger-hover': buttonShadow('225 29 72', true),
        'btn-success': buttonShadow('5 150 105', false),
        'btn-success-hover': buttonShadow('5 150 105', true),
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
      // Hairline top highlight for elevated dark surfaces (see Card).
      ringColor: {
        ...accentTints,
        edge: 'rgb(255 255 255 / 0.05)',
      },
    },
  },
  plugins: [
    plugin(({ addBase }) => {
      addBase({
        ':root': accentVariables(false),
        ':root.dark': accentVariables(true),
      });
    }),
  ],
}
