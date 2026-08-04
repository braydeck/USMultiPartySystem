import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

// Typography is declared in src/constants/typography.ts and tailwind.config.js. These rules
// exist because the alternative was tried: with nothing enforcing the scale, the app grew 273
// arbitrary `text-[Npx]` values and 48 bare SVG `fontSize` numbers. Both selectors are needed
// in each pair — most classNames here are template literals, which a `Literal` selector misses.
const SIZE_MSG =
  'Use a named font size (text-4xs … text-3xl). If no step fits, add one to tailwind.config.js.'
const CHART_MSG =
  'Use CHART_TYPE from src/constants/typography.ts instead of a raw fontSize number.'

const TYPOGRAPHY_RULES = [
  { selector: 'Literal[value=/text-\\[[0-9.]+px\\]/]', message: SIZE_MSG },
  { selector: 'TemplateElement[value.raw=/text-\\[[0-9.]+px\\]/]', message: SIZE_MSG },
  {
    selector: 'JSXAttribute[name.name="fontSize"] > JSXExpressionContainer > Literal[value>0]',
    message: CHART_MSG,
  },
  { selector: 'Property[key.name="fontSize"] > Literal[value>0]', message: CHART_MSG },
]

export default defineConfig([
  globalIgnores(['dist', 'functions']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      'no-restricted-syntax': ['error', ...TYPOGRAPHY_RULES],
    },
  },
  {
    // Dead code, kept for reference and not migrated. Already carries pre-existing errors.
    files: ['src/tabs/archive/**'],
    rules: { 'no-restricted-syntax': 'off' },
  },
])
