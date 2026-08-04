/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        sans: ['Geist Sans', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Geist Mono', 'ui-monospace', 'monospace'],
      },
      // Steps below Tailwind's 12px floor. This app is data-dense — chart labels, legend
      // chips, cartogram tooltips, table cells — and genuinely needs them. Naming them
      // here is what keeps `text-[10px]` out of the source. Descending, so 2xs > 3xs > 4xs.
      //
      // Size only, no paired line-height, unlike the stock steps. These replaced ~250
      // `text-[Npx]` utilities, which set font-size alone and left line-height inherited;
      // pairing a line-height here would silently retighten 206 dense rows that never had
      // one. Pair them deliberately, checking the layouts, not as a side effect of naming.
      fontSize: {
        '2xs': '0.6875rem', // 11px
        '3xs': '0.625rem',  // 10px
        '4xs': '0.5625rem', //  9px
      },
    },
  },
  plugins: [],
}
