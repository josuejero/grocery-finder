"use client";

import * as React from "react";
import { DayPicker } from "react-day-picker";
import "react-day-picker/dist/style.css";

interface DatePickerProps {
  date?: Date;
  onDateChange: (date: Date | undefined) => void;
}

export const DatePicker: React.FC<DatePickerProps> = ({ date, onDateChange }) => {
  return (
    <DayPicker
      mode="single"
      selected={date}
      onSelect={onDateChange}
    />
  );
};
