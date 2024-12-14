import { useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert } from "@/components/ui/alert";

interface LoginFormData {
  username: string;
  password: string;
}

export default function LoginForm() {
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const { login } = useAuthStore();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<LoginFormData>();

  const onSubmit = async (data: LoginFormData) => {
    try {
      setError(null);
      await login(data);
      console.log("Before redirecting to /dashboard");
      router.push('/dashboard'); // Confirm this executes
      console.log("After redirecting to /dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Input
          {...register("username", { required: "Username is required" })}
          type="text"
          placeholder="Username"
          error={!!errors.username}
          helperText={errors.username?.message}
        />
      </div>

      <div className="space-y-2">
        <Input
          {...register("password", { required: "Password is required" })}
          type="password"
          placeholder="Password"
          error={!!errors.password}
          helperText={errors.password?.message}
        />
      </div>

      {error && (
        <Alert variant="destructive">
          {error}
        </Alert>
      )}

      <Button
        type="submit"
        className="w-full"
        disabled={isSubmitting}
      >
        {isSubmitting ? "Signing in..." : "Sign in"}
      </Button>

      <p className="text-center text-sm text-gray-600">
        Don&apos;t have an account?{" "}
        <Link href="/auth/register" className="text-blue-600 hover:underline">
          Register
        </Link>
      </p>
    </form>
  );
}
