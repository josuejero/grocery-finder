export const API_ENDPOINTS = {
  auth: {
    login: '/auth/login',
    register: '/auth/register'
  },
  profile: '/users/me',
  shoppingLists: '/users/me/shopping-lists'
};

export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';