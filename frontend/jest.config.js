// jest.config.js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jest-environment-jsdom', // Use the package name directly
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1', // Ensure <rootDir> is included
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  transform: {
    '^.+\\.tsx?$': 'ts-jest',
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
};
