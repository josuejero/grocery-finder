export interface ShoppingListItem {
  name: string;
  quantity: number;
  notes?: string;
}

export interface ShoppingList {
  id: number;
  name: string;
  items: Array<{ name: string; quantity: number }>;
}
export interface CreateShoppingListData {
  name: string;
  items: ShoppingListItem[];
}

export interface UpdateShoppingListData {
  name?: string;
  items?: ShoppingListItem[];
  is_active?: boolean;
}