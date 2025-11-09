/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        surface: '#0f1117',
        panel: '#171b24',
        accent: '#4cc2ff',
        border: '#242a38',
        muted: '#7b839a'
      },
      boxShadow: {
        toolbar: '0 1px 0 0 rgba(255, 255, 255, 0.05)',
        panel: '0 0 20px rgba(0, 0, 0, 0.45)'
      }
    }
  }
};
