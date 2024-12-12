// frontend/src/api/base.ts
export const API_ENDPOINTS = {
  auth: {
    login: '/auth/login',
    register: '/auth/register'
  },
  profile: '/users/me',  // Changed from /api/profile
  shoppingLists: '/users/me/shopping-lists'
};

export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';