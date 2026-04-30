import { useState } from "react";
import { Bell, TrendingUp, Search, BarChart2, Settings as SettingsIcon, LucideIcon } from "lucide-react";
import AlertFeed from "./components/AlertFeed";
import PriceChart from "./components/PriceChart";
import SearchProfiles from "./components/SearchProfiles";
import Stats from "./components/Stats";
import Settings from "./components/Settings";

type Tab = "alerts" | "chart" | "profiles" | "stats" | "settings";

const NAV: { key: Tab; label: string; Icon: LucideIcon }[] = [
  { key: "alerts", label: "Alerts", Icon: Bell },
  { key: "chart", label: "Preishistorie", Icon: TrendingUp },
  { key: "profiles", label: "Suchprofile", Icon: Search },
  { key: "stats", label: "Stats", Icon: BarChart2 },
  { key: "settings", label: "Einstellungen", Icon: SettingsIcon },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("alerts");

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <aside className="w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col py-6 gap-1">
        <div className="px-5 mb-6">
          <h1 className="text-lg font-bold text-white">Flipper</h1>
          <p className="text-xs text-gray-500">Willhaben Bot</p>
        </div>
        {NAV.map(({ key, label, Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-3 px-5 py-2.5 text-sm font-medium rounded-lg mx-2 transition-colors ${
              tab === key
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
          >
            <Icon size={17} />
            {label}
          </button>
        ))}
      </aside>

      <main className="flex-1 overflow-y-auto p-6">
        {tab === "alerts" && <AlertFeed />}
        {tab === "chart" && <PriceChart />}
        {tab === "profiles" && <SearchProfiles />}
        {tab === "stats" && <Stats />}
        {tab === "settings" && <Settings />}
      </main>
    </div>
  );
}
