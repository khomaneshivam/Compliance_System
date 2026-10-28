import '@testing-library/jest-dom';

// Mock window.alert for jsdom environment
if (typeof window !== 'undefined') {
  window.alert = () => {};
}
