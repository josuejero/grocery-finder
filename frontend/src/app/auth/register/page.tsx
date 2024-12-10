"use client";

import { useForm } from "react-hook-form";
import { useAuthStore } from "@/store/auth";

interface RegisterFormInputs {
  username: string;
  email: string;
  password: string;
}

export default function RegisterPage() {
  const { register: registerUser, error, isLoading } = useAuthStore();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormInputs>();

  const onSubmit = async (data: RegisterFormInputs) => {
    try {
      await registerUser(data);
      alert("Registration successful");
    } catch (err) {
      alert(err);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen">
      <h1 className="text-2xl font-bold mb-4">Register</h1>
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
          type="email"
          placeholder="Email"
          {...register("email", { required: true })}
          className="p-2 border rounded"
        />
        {errors.email && <p className="text-red-500">Email is required</p>}

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
          className="bg-green-500 text-white p-2 rounded"
        >
          {isLoading ? "Registering..." : "Register"}
        </button>
        {error && <p className="text-red-500">{error}</p>}
      </form>
    </div>
  );
}
