// frontend/src/app/shopping-lists/[id]/page.tsx

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { getShoppingList, updateShoppingList } from "@/api/shopping-lists";
import type { ShoppingList } from "@/types/shopping";

export default function ShoppingListDetailPage() {
  const params = useParams();
  const [list, setList] = useState<ShoppingList | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [newItem, setNewItem] = useState({ name: "", quantity: 1 });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchList = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        if (!params?.id) {
          throw new Error("No shopping list ID provided");
        }

        const data = await getShoppingList(Number(params.id));
        setList(data);
      } catch (error) {
        console.error("Failed to fetch shopping list:", error);
        setError("Failed to load shopping list. Please try again later.");
      } finally {
        setIsLoading(false);
      }
    };

    if (params?.id) {
      fetchList();
    }
  }, [params?.id]);

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!list || !newItem.name) return;

    try {
      setError(null);
      const updatedItems = [...list.items, newItem];
      const updatedList = await updateShoppingList(list.id, {
        items: updatedItems
      });
      setList(updatedList);
      setNewItem({ name: "", quantity: 1 });
    } catch (error) {
      console.error("Failed to add item:", error);
      setError("Failed to add item. Please try again.");
    }
  };

  const handleDeleteItem = async (index: number) => {
    if (!list) return;

    try {
      setError(null);
      const updatedItems = list.items.filter((_, i) => i !== index);
      const updatedList = await updateShoppingList(list.id, {
        items: updatedItems
      });
      setList(updatedList);
    } catch (error) {
      console.error("Failed to delete item:", error);
      setError("Failed to delete item. Please try again.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-4">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!list) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Shopping list not found</div>
      </div>
    );
  }

  return (
    <ProtectedRoute>
      <div className="container mx-auto p-4 max-w-4xl">
        <Card>
          <CardHeader>
            <CardTitle>{list.name}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAddItem} className="flex gap-2 mb-4">
              <Input
                type="text"
                placeholder="Item name"
                value={newItem.name}
                onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                className="flex-1"
              />
              <Input
                type="number"
                min="1"
                value={newItem.quantity}
                onChange={(e) =>
                  setNewItem({ ...newItem, quantity: parseInt(e.target.value) })
                }
                className="w-24"
              />
              <Button type="submit">Add Item</Button>
            </form>

            <div className="space-y-2">
              {list.items.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-2 border rounded"
                >
                  <div>
                    <span className="font-medium">{item.name}</span>
                    <span className="ml-2 text-gray-500">
                      Qty: {item.quantity}
                    </span>
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDeleteItem(index)}
                  >
                    Delete
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  );
}