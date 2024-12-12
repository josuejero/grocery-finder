import { format, parseISO } from "date-fns";

export function formatDate(date: string, formatString: string = "yyyy-MM-dd"): string {
    return format(parseISO(date), formatString);
}

export function isToday(date: Date): boolean {
    const today = new Date();
    return today.toDateString() === date.toDateString();
}
