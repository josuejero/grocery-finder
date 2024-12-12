import { z } from "zod";

export const emailValidation = z.string().email("Invalid email address");
export const passwordValidation = z.string().min(6, "Password must be at least 6 characters long");

export function validateUsername(username: string): boolean {
    return /^[a-zA-Z0-9]+$/.test(username); // Alphanumeric only
}
