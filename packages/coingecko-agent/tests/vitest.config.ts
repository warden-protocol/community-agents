import {
  configDefaults,
  coverageConfigDefaults,
  defineConfig,
} from 'vitest/config';
import { loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  // Load environment variables from .env files
  const env = loadEnv(mode, process.cwd(), '');

  return {
    test: {
      exclude: [...configDefaults.exclude, 'build/**/*'],
      coverage: {
        provider: 'v8',
        exclude: [...coverageConfigDefaults.exclude, 'build/**/*'],
      },
      testTimeout: 60000,
      env: {
        // Pass environment variables to test environment
        ...env,
      },
    },
  };
});
