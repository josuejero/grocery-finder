import ProtectedRoute from "@/components/auth/ProtectedRoute";

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <div className="flex flex-col items-center justify-center h-screen">
        <h1 className="text-2xl font-bold">User Profile</h1>
        <p>Welcome to your profile page!</p>
      </div>
    </ProtectedRoute>
  );
}
