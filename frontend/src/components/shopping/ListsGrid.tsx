import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

interface ShoppingList {
  id: string;
  name: string;
  items: Array<{ name: string; quantity: number }>;
}

interface ListsGridProps {
  lists: ShoppingList[];
}

export default function ListsGrid({ lists }: ListsGridProps) {
  if (lists.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        No shopping lists yet. Create one to get started!
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {lists.map((list) => (
        <Link key={list.id} href={`/shopping-lists/${list.id}`}>
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader>
              <CardTitle>{list.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-gray-500">
                {list.items.length} items
              </div>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}