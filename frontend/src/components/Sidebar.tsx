import { Users, Wrench, Building2, Plus, Sparkles } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

const nav = [
  { label: "Hire", icon: Plus, href: "/" },
  { label: "Workers", icon: Users, href: "/" },
  { label: "Tools", icon: Wrench, href: "/" },
  { label: "Organizations", icon: Building2, href: "/" },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <div className="w-56 bg-white border-r border-gray-100 flex flex-col h-screen">
      <div className="px-5 py-5 flex items-center gap-2 border-b border-gray-100">
        <Sparkles size={18} className="text-green-600" />
        <span className="font-bold text-gray-900">AI Workers</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map(item => (
          <Link
            key={item.label}
            to={item.href}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
              location.pathname === item.href && item.label === "Workers"
                ? "bg-gray-100 font-medium text-gray-900"
                : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <item.icon size={16} />
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="px-3 py-4 border-t border-gray-100 space-y-1">
        <button className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50 w-full">
          <Sparkles size={16} />
          What's New
        </button>
        <div className="flex items-center gap-2 px-3 py-2 text-xs text-gray-400">
          <div className="w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center font-bold text-xs">G</div>
          goncalo@unicornfactory
        </div>
      </div>
    </div>
  );
}