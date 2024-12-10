// src/types/priceComparison.ts

export interface Price {
  storeName: string;
  amount: number;
}

export interface PriceComparisonResult {
  productName: string;
  prices: Price[];
}
