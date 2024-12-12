import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DatePicker } from "@/components/ui/date-picker";

interface SearchFilters {
  productName?: string;
  startDate?: string;
  endDate?: string;
  storeIds?: string;
}

interface PriceFilterProps {
  onSearch: (filters: SearchFilters) => void;
  isLoading: boolean;
}

export default function PriceFilter({ onSearch, isLoading }: PriceFilterProps) {
  const [productName, setProductName] = useState("");
  const [startDate, setStartDate] = useState<Date | undefined>(undefined);
  const [endDate, setEndDate] = useState<Date | undefined>(undefined);
  // Remove storeIds if not used:
  // const [storeIds, setStoreIds] = useState<string[]>([]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch({
      productName,
      startDate: startDate?.toISOString(),
      endDate: endDate?.toISOString(),
      // storeIds: storeIds.join(",")
    });
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Input
              type="text"
              placeholder="Product name"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
            />
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Start Date</label>
              <DatePicker 
                date={startDate}
                onDateChange={setStartDate}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">End Date</label>
              <DatePicker 
                date={endDate}
                onDateChange={setEndDate}
              />
            </div>

            <Button 
              type="submit" 
              disabled={isLoading || !productName}
              className="self-end"
            >
              {isLoading ? "Searching..." : "Search"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
