"use client";

import { ReactNode, useEffect } from "react";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";

interface ProtectedRouteProps {
  children: ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return null; // Optionally, add a loading spinner here
  }

  return <>{children}</>;
}
