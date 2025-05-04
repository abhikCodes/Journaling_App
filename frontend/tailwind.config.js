module.exports = {
    darkMode: 'class',
    content: ['./index.html', './src/**/*.{js,jsx}'],
    theme: {
      extend: {
        colors: {
          primary: {
            DEFAULT: '#58CC02',
            hover: '#46A302',
            dark: '#2B7002'
          },
          secondary: {
            DEFAULT: '#FFC800',
            hover: '#E5B400',
            dark: '#CC9B00'
          },
          accent: {
            DEFAULT: '#FF4B4B',
            hover: '#E54343',
            dark: '#CC3333'
          },
          midnight: {
            DEFAULT: '#1CB0F6',
            hover: '#189EE0',
            dark: '#146A94'
          },
          background: '#FFF9E5',
          surface: '#FFFFFF',
          text: {
            DEFAULT: '#4B4B4B',
            light: '#777777',
            dark: '#1F1F1F'
          }
        },
        fontFamily: {
          sans: ['Nunito', 'sans-serif'],
          serif: ['Playfair Display', 'serif'],
          baskerville: ['Libre Baskerville', 'serif'],
        },
        boxShadow: {
          'btn': '0px 4px 0px 0px #46A302',
          'btn-hover': '0px 2px 0px 0px #46A302',
          'card': '0px 2px 8px rgba(0,0,0,0.1)',
        },
        borderRadius: {
          'xl': '1rem',
          '2xl': '1.5rem',
        },
      }
    },
    plugins: []
  }