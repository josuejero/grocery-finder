// src/app/price-comparison/page.tsx

"use client";

import { useState } from "react";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { PriceComparisonResult, Price } from "@/types/priceComparison"; // Import the interfaces

export default function PriceComparisonPage() {
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [results, setResults] = useState<PriceComparisonResult[]>([]); // Use the defined interface

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const response = await fetch(`/api/prices/compare?query=${searchTerm}`);
      const data: PriceComparisonResult[] = await response.json(); // Type the response
      setResults(data);
    } catch (error) {
      console.error('Failed to fetch price comparisons:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex flex-col items-center justify-start min-h-screen p-4">
        <div className="w-full max-w-4xl">
          <h1 className="text-2xl font-bold mb-6">Price Comparison</h1>
          
          <form onSubmit={handleSearch} className="flex gap-2 mb-6">
            <Input
              type="text"
              placeholder="Search for products..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Searching..." : "Search"}
            </Button>
          </form>

          <div className="grid gap-4">
            {results.map((result, index) => (
              <Card key={index}>
                <CardHeader>
                  <CardTitle>{result.productName}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {result.prices?.map((price: Price, priceIndex: number) => ( // Use the Price interface
                      <div key={priceIndex} className="flex justify-between items-center">
                        <span>{price.storeName}</span>
                        <span className="font-semibold">
                          ${price.amount.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {results.length === 0 && (
            <div className="text-center text-gray-500 mt-8">
              Search for products to see price comparisons
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
