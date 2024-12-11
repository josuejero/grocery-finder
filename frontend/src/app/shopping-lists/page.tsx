"use client";

import React, { useEffect, useState } from "react";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import CreateListDialog from "@/components/shopping/CreateListDialog";
import ListsGrid from "@/components/shopping/ListsGrid";

export default function ShoppingListsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [lists, setLists] = useState([]);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  useEffect(() => {
    const fetchLists = async () => {
      try {
        const response = await fetch("/api/shopping-lists");
        const data = await response.json();
        setLists(data);
      } catch (error) {
        console.error("Failed to fetch shopping lists:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchLists();
  }, []);

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
            {isLoading ? (
              <div className="flex justify-center p-4">Loading...</div>
            ) : (
              <ListsGrid lists={lists} />
            )}
          </CardContent>
        </Card>

        <CreateListDialog
          open={isCreateDialogOpen}
          onOpenChange={setIsCreateDialogOpen}
        />
      </div>
    </ProtectedRoute>
  );
}