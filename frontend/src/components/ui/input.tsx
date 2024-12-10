// src/components/ui/input.tsx

import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  helperText?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, helperText, ...props }, ref) => {
    return (
      <div className="flex flex-col">
        <input
          type={type}
          className={cn(
            "flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm",
            error ? "border-red-500" : "border-input",
            className
          )}
          ref={ref}
          {...props}
        />
        {helperText && (
          <span className={cn("text-xs mt-1", error ? "text-red-500" : "text-muted-foreground")}>
            {helperText}
          </span>
        )}
      </div>
    )
  }
)
Input.displayName = "Input"

export { Input }
