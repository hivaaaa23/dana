// ساخت CSS لوکال به‌جای Tailwind CDN. دستور ساخت در README.md ریشه‌ی پروژه آمده.
module.exports = {
  content: [require('path').join(__dirname, '../frontend/*.html'), require('path').join(__dirname, '../frontend/js/*.js')],
  theme: {
    extend: {
      fontFamily: { sans: ['Vazirmatn', 'sans-serif'] },
      colors: {
        base: '#14151f', surface: '#1a1c29', raised: '#1f2231',
        line: '#2a2d3e', ink: '#edeef2', muted: '#9296ac',
        accent: '#e8a33d', cyan: '#4dd6c4', danger: '#e2685f',
      },
    },
  },
};
