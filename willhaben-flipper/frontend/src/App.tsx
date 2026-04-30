import { useState } from "react";
import {
  Bell,
  TrendingUp,
  Search,
  BarChart2,
  Settings as SettingsIcon,
  Zap,
  LucideIcon,
} from "lucide-react";
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
    <div style={{ display: "flex", height: "100vh", background: "#11151c", overflow: "hidden" }}>
      <aside
        style={{
          width: "220px",
          flexShrink: 0,
          background: "#11151c",
          borderRight: "1px solid rgba(84,101,255,0.1)",
          display: "flex",
          flexDirection: "column",
          padding: "24px 0 16px",
        }}
      >
        <div style={{ padding: "0 20px 28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "3px" }}>
            <Zap size={18} color="#5465ff" fill="#5465ff" />
            <span style={{ fontSize: "16px", fontWeight: 700, color: "#f0f4ff" }}>MilkFlip</span>
          </div>
          <p style={{ fontSize: "11px", color: "#4a5568", paddingLeft: "26px" }}>Willhaben Bot</p>
        </div>

        <nav style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
          {NAV.map(({ key, label, Icon }) => {
            const active = tab === key;
            return (
              <button
                key={key}
                onClick={() => setTab(key)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "9px 20px",
                  fontSize: "13px",
                  fontWeight: active ? 600 : 500,
                  color: active ? "#788bff" : "#8a97b0",
                  background: active ? "rgba(84,101,255,0.12)" : "transparent",
                  border: "none",
                  borderLeft: active ? "3px solid #5465ff" : "3px solid transparent",
                  width: "100%",
                  textAlign: "left",
                  transition: "all 0.15s ease",
                  cursor: "pointer",
                  outline: "none",
                }}
                onMouseEnter={(e) => {
                  if (!active) {
                    e.currentTarget.style.color = "#f0f4ff";
                    e.currentTarget.style.background = "rgba(84,101,255,0.06)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!active) {
                    e.currentTarget.style.color = "#8a97b0";
                    e.currentTarget.style.background = "transparent";
                  }
                }}
              >
                <Icon size={16} />
                {label}
              </button>
            );
          })}
        </nav>
      </aside>

      <main
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "32px 36px",
          background: "#11151c",
        }}
      >
        {tab === "alerts" && <AlertFeed />}
        {tab === "chart" && <PriceChart />}
        {tab === "profiles" && <SearchProfiles />}
        {tab === "stats" && <Stats />}
        {tab === "settings" && <Settings />}
      </main>
    </div>
  );
}
