import apiClient from '@/utils/api';
import type { ShoppingList, CreateShoppingListData, UpdateShoppingListData } from '@/types/shopping';
import axios from 'axios';

export const getShoppingList = async (id: number): Promise<ShoppingList> => {
  const response = await apiClient.get(`/users/me/shopping-lists/${id}`);
  return response.data;
};

export const getShoppingLists = async (): Promise<ShoppingList[]> => {
  try {
    // Add debug logging
    console.log('📋 Fetching shopping lists...');
    // console.log('🔑 Current auth token:', localStorage.getItem('auth-token'));

    const response = await apiClient.get('/users/me/shopping-lists');
    console.log('📋 Shopping lists response:', response.data);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error('❌ Shopping lists error details:', {
        message: error.message,
        status: error.response?.status,
        data: error.response?.data,
        requestHeaders: error.config?.headers
      });
    } else {
      console.error('❌ An unexpected error occurred:', error);
    }
    throw error;
  }
};

export const createShoppingList = async (data: CreateShoppingListData): Promise<ShoppingList> => {
  try {
    const response = await apiClient.post('/users/me/shopping-lists', data);
    return response.data;
  } catch (error: unknown) {
    if (axios.isAxiosError(error)) {
      console.error('❌ Create shopping list error details:', {
        message: error.message,
        status: error.response?.status,
        data: error.response?.data,
        requestHeaders: error.config?.headers
      });
    } else {
      console.error('❌ An unexpected error occurred:', error);
    }
    throw error;
  }
};

export const updateShoppingList = async (id: number, data: UpdateShoppingListData): Promise<ShoppingList> => {
  try {
    const response = await apiClient.put(`/users/me/shopping-lists/${id}`, data);
    return response.data;
  } catch (error: unknown) {
    if (axios.isAxiosError(error)) {
      console.error('❌ Update shopping list error details:', {
        message: error.message,
        status: error.response?.status,
        data: error.response?.data,
        requestHeaders: error.config?.headers
      });
    } else {
      console.error('❌ An unexpected error occurred:', error);
    }
    throw error;
  }
};

export const deleteShoppingList = async (id: number): Promise<void> => {
  try {
    await apiClient.delete(`/users/me/shopping-lists/${id}`);
  } catch (error: unknown) {
    if (axios.isAxiosError(error)) {
      console.error('❌ Delete shopping list error details:', {
        message: error.message,
        status: error.response?.status,
        data: error.response?.data,
        requestHeaders: error.config?.headers
      });
    } else {
      console.error('❌ An unexpected error occurred:', error);
    }
    throw error;
  }
};
