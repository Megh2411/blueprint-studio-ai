/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: '#0a0a0a',
        darker: '#050505',
        neon: '#3b82f6', // A sleek, electric blue
      },
      boxShadow: {
        'glow': '0 0 40px -10px rgba(59, 130, 246, 0.5)',
      }
    },
  },
  plugins: [],
}