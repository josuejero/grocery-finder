"use client";

import { ReactNode, useEffect, useState } from "react";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";

interface ProtectedRouteProps {
  children: ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, token, isLoading } = useAuthStore();
  const router = useRouter();
  const [isHydrated, setIsHydrated] = useState(false);

  // Wait for zustand state hydration
  useEffect(() => {
    setIsHydrated(true);
  }, []);

  useEffect(() => {
    if (isHydrated && !isLoading && (!isAuthenticated || !token)) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, isLoading, isHydrated, router, token]);

  if (!isHydrated || isLoading) {
    return <div>Loading...</div>; // Prevent rendering children until state is ready
  }

  return <>{children}</>;
}
