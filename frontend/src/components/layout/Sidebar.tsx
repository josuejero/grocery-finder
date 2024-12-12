import Link from "next/link";
import { 
  Home, 
  ShoppingCart, 
  TrendingUp, 
  List, 
  Settings, 
  User 
} from "lucide-react";

export default function Sidebar() {

  const menuItems = [
    { label: "Dashboard", icon: Home, href: "/dashboard" },
    { label: "Price Comparison", icon: TrendingUp, href: "/price-comparison" },
    { label: "Shopping Lists", icon: ShoppingCart, href: "/shopping-lists" },
    { label: "Products", icon: List, href: "/products" },
    { label: "Profile", icon: User, href: "/profile" },
    { label: "Settings", icon: Settings, href: "/settings" }
  ];

  return (
    <aside className="fixed left-0 top-16 w-64 h-[calc(100vh-4rem)] bg-white border-r border-gray-200 overflow-y-auto">
      <nav className="p-4 space-y-2">
        {menuItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-gray-100 text-gray-700 hover:text-gray-900"
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}