import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import PriceFilter from "./PriceFilter";
import { PriceChart } from "./PriceChart";
import { TrendChart } from "./TrendChart";

interface PriceData {
  storeName: string;
  price: number;
  date: string;
}

interface Product {
  id: string;
  name: string;
  prices: PriceData[];
}

interface SearchFilters {
  productName?: string;
  startDate?: string;
  endDate?: string;
  storeIds?: string;
}

export default function PriceComparison() {
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  // Remove this since not used:
  // const [dateRange, setDateRange] = useState<{ start: Date; end: Date } | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = async (filters: SearchFilters) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/prices/compare?${new URLSearchParams(filters as Record<string, string>)}`);
      const data = await response.json();
      setSelectedProduct(data);
    } catch (error) {
      console.error("Failed to fetch price data:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PriceFilter onSearch={handleSearch} isLoading={isLoading} />
      
      {selectedProduct && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Current Prices - {selectedProduct.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <PriceChart
                data={selectedProduct.prices.map(({ storeName, price }) => ({
                  store: storeName,
                  price,
                }))}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Price Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <TrendChart 
                data={selectedProduct.prices.map(({ date, price }) => ({
                  date,
                  value: price,
                }))}
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
