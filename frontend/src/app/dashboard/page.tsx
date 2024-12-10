"use client";

import ProtectedRoute from "@/components/auth/ProtectedRoute";

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <div className="flex flex-col items-center justify-center min-h-screen p-4">
        <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full max-w-7xl">
          <div className="p-6 rounded-lg border shadow-sm">
            <h2 className="text-xl font-semibold mb-2">Recent Shopping Lists</h2>
            <p className="text-gray-600">View your recent shopping lists here</p>
          </div>
          
          <div className="p-6 rounded-lg border shadow-sm">
            <h2 className="text-xl font-semibold mb-2">Price Comparisons</h2>
            <p className="text-gray-600">Compare prices across different stores</p>
          </div>
          
          <div className="p-6 rounded-lg border shadow-sm">
            <h2 className="text-xl font-semibold mb-2">Profile Settings</h2>
            <p className="text-gray-600">Update your preferences and profile</p>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}