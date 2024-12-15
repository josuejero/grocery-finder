"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import ListsGrid from "@/components/shopping/ListsGrid"; // Changed to default import
import { getShoppingLists } from "@/api/shopping-lists";
import { Alert } from "@/components/ui/alert";
import { ShoppingList } from "@/types/shopping"; // Import the ShoppingList type

export default function ShoppingListsPage() {
  const router = useRouter();
  const { isAuthenticated, token } = useAuthStore();
  const [lists, setLists] = useState<ShoppingList[]>([]); // Specify type
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null); // Specify type

  const fetchLists = useCallback(async () => {
    if (!isAuthenticated || !token) {
      router.push("/auth/login");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const data = await getShoppingLists();
      setLists(data as ShoppingList[]); // Ensure data matches ShoppingList[]
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch shopping lists");
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, token, router]);

  useEffect(() => {
    fetchLists();
  }, [fetchLists]);

  if (!isAuthenticated) {
    return null; // Let the router handle the redirect
  }

  if (error) {
    return <Alert variant="destructive">{error}</Alert>;
  }

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="container mx-auto p-4">
      <ListsGrid lists={lists} />
    </div>
  );
}
