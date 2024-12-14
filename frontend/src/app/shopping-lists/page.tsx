"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import { getShoppingLists } from "@/api/shopping-lists";
import type { ShoppingList } from "@/types/shopping";
import ListsGrid from "@/components/shopping/ListsGrid";
import CreateListDialog from "@/components/shopping/CreateListDialog";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

// If you're using Axios, uncomment the following line
// import { AxiosError } from "axios";

export default function ShoppingListsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lists, setLists] = useState<ShoppingList[]>([]);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const { isAuthenticated, token } = useAuthStore();
  const router = useRouter();

  const fetchLists = useCallback(async () => {
    const storedToken = localStorage.getItem("auth-token");
    console.log(
      "🔑 Stored token:",
      storedToken ? storedToken.substring(0, 20) + "..." : "none"
    );

    if (!storedToken) {
      console.warn("⚠️ No token found, redirecting to login");
      router.push("/auth/login");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const data = await getShoppingLists();
      setLists(data);
    } catch (err: unknown) {
      // Handle standard Error
      if (err instanceof Error) {
        console.error("❌ Fetch error message:", err.message);
        setError(err.message);
      }
      // If using Axios, handle AxiosError
      // else if (axios.isAxiosError(err)) {
      //   console.error("❌ Axios fetch error:", {
      //     message: err.message,
      //     response: err.response?.data,
      //     status: err.response?.status,
      //   });
      //   setError(err.response?.data?.message || err.message);
      // }
      // Handle other types of errors
      else {
        console.error("❌ An unexpected error occurred:", err);
        setError("An unexpected error occurred.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    console.log("🔍 Auth state:", { isAuthenticated, token });
    if (isAuthenticated && token) {
      fetchLists();
    }
  }, [isAuthenticated, token, fetchLists]);

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          {error}
          <pre className="mt-2 text-sm">
            {JSON.stringify({ isAuthenticated, hasToken: !!token }, null, 2)}
          </pre>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <ProtectedRoute>
      <div className="container mx-auto p-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Shopping Lists</CardTitle>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              Create New List
            </Button>
          </CardHeader>
          <CardContent>
            {error ? (
              <div className="text-red-500 text-center p-4">{error}</div>
            ) : isLoading ? (
              <div className="flex justify-center p-4">Loading...</div>
            ) : (
              <ListsGrid lists={lists} />
            )}
          </CardContent>
        </Card>

        <CreateListDialog
          open={isCreateDialogOpen}
          onOpenChange={setIsCreateDialogOpen}
          onSuccess={async () => {
            setIsCreateDialogOpen(false);
            await fetchLists();
          }}
        />
      </div>
    </ProtectedRoute>
  );
}
