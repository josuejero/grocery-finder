"use client";

import { useForm } from "react-hook-form";
import { useAuthStore } from "@/store/auth";

interface LoginFormInputs {
  username: string;
  password: string;
}

export default function LoginPage() {
  const { login, error, isLoading } = useAuthStore();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormInputs>();

  const onSubmit = async (data: LoginFormInputs) => {
    try {
      await login(data);
      alert("Login successful");
      window.location.href = "/dashboard";
    } catch {
      alert("Login failed. Please try again.");
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen">
      <h1 className="text-2xl font-bold mb-4">Login</h1>
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="flex flex-col gap-4 w-full max-w-sm"
      >
        <input
          type="text"
          placeholder="Username"
          {...register("username", { required: true })}
          className="p-2 border rounded"
        />
        {errors.username && <p className="text-red-500">Username is required</p>}

        <input
          type="password"
          placeholder="Password"
          {...register("password", { required: true })}
          className="p-2 border rounded"
        />
        {errors.password && <p className="text-red-500">Password is required</p>}

        <button
          type="submit"
          disabled={isLoading}
          className="bg-blue-500 text-white p-2 rounded"
        >
          {isLoading ? "Logging in..." : "Login"}
        </button>
        {error && <p className="text-red-500">{error}</p>}
      </form>
    </div>
  );
}
