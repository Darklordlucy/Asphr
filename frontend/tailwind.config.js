/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        brush: ['"Caveat Brush"', 'cursive'],
        heading: ['Montserrat', 'sans-serif'],
      },
      colors: {
        brand: {
          yellow: '#FFD700',
          dark: '#0F2027',
          green: '#4CAF50',
          orange: '#FF9800',
          blue: '#2196F3',
          purple: '#9C27B0'
        }
      }
    },
  },
  plugins: [],
}
