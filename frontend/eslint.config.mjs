export default [
  {
    // P6-01 owns executable dependencies and TypeScript/React rules.
    ignores: [
      'node_modules/**',
      'dist/**',
      'coverage/**',
      '.vite/**',
      'playwright-report/**',
      'test-results/**',
    ],
  },
];
