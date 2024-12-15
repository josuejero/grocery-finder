// frontend/src/components/shopping/CreateListDialog.tsx

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createShoppingList } from "@/api/shopping-lists";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface CreateListDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => Promise<void>;
}

export default function CreateListDialog({ 
  open, 
  onOpenChange, 
  onSuccess 
}: CreateListDialogProps) {
  const [name, setName] = useState("");
  const [items, setItems] = useState([{ name: "", quantity: 1 }]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAddItem = () => {
    setItems([...items, { name: "", quantity: 1 }]);
  };

  const handleItemChange = (index: number, field: 'name' | 'quantity', value: string | number) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], [field]: value };
    setItems(newItems);
  };

  const handleRemoveItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("List name is required");
      return;
    }

    const validItems = items.filter(item => item.name.trim());
    if (validItems.length === 0) {
      setError("At least one item is required");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await createShoppingList({
        name: name.trim(),
        items: validItems
      });
      setName("");
      setItems([{ name: "", quantity: 1 }]);
      onOpenChange(false);
      await onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create shopping list");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create New Shopping List</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="List name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          
          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  placeholder="Item name"
                  value={item.name}
                  onChange={(e) => handleItemChange(index, 'name', e.target.value)}
                  className="flex-1"
                />
                <Input
                  type="number"
                  min="1"
                  value={item.quantity}
                  onChange={(e) => handleItemChange(index, 'quantity', parseInt(e.target.value))}
                  className="w-20"
                />
                {items.length > 1 && (
                  <Button 
                    type="button"
                    variant="destructive"
                    onClick={() => handleRemoveItem(index)}
                  >
                    Remove
                  </Button>
                )}
              </div>
            ))}
          </div>

          <Button
            type="button"
            variant="outline"
            onClick={handleAddItem}
            className="w-full"
          >
            Add Item
          </Button>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="flex justify-end space-x-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}