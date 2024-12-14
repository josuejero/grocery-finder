"use client";

import AppLayout from "@/components/layout/AppLayout";

export default function Home() {
  return (
    <AppLayout>
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-theme(spacing.16))]">
        <h1 className="text-4xl font-bold mb-8">Welcome to Grocery Finder</h1>
        <p className="text-xl text-gray-600">Find the best prices for your groceries</p>
      </div>
    </AppLayout>
  );
}