import { useEffect, useState } from "react";
import { Eye, Bell, TrendingUp, DollarSign, LucideIcon } from "lucide-react";
import { api, StatsData } from "../api";

function MetricCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  accent: string;
}) {
  return (
    <div
      style={{
        background: "#19212e",
        border: "1px solid rgba(84,101,255,0.15)",
        borderRadius: "12px",
        padding: "20px",
        display: "flex",
        alignItems: "center",
        gap: "16px",
      }}
    >
      <div
        style={{
          background: `${accent}18`,
          borderRadius: "10px",
          padding: "10px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <Icon size={20} color={accent} />
      </div>
      <div>
        <p style={{ fontSize: "26px", fontWeight: 700, color: "#f0f4ff", lineHeight: 1 }}>
          {value}
        </p>
        <p style={{ fontSize: "12px", color: "#8a97b0", marginTop: "5px" }}>{label}</p>
      </div>
    </div>
  );
}

export default function Stats() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.stats.get().then((s) => {
      setStats(s);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "64px 0", color: "#4a5568" }}>
        <div className="pulse" style={{ fontSize: "13px" }}>Lade Stats…</div>
      </div>
    );
  }
  if (!stats) return null;

  return (
    <div style={{ maxWidth: "720px", margin: "0 auto" }}>
      <h2 style={{ fontSize: "20px", fontWeight: 700, color: "#f0f4ff", marginBottom: "24px" }}>
        Statistiken
      </h2>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "24px" }}>
        <MetricCard label="Heute gesehen" value={stats.today_seen.toLocaleString()} icon={Eye} accent="#5465ff" />
        <MetricCard label="Heute Alerts" value={stats.today_alerts.toLocaleString()} icon={Bell} accent="#f59e0b" />
        <MetricCard
          label="Beste Marge heute"
          value={stats.best_margin_today != null ? `${stats.best_margin_today.toFixed(0)}€` : "—"}
          icon={TrendingUp}
          accent="#22d3a5"
        />
        <MetricCard
          label="Gesamtgewinn (Interessiert)"
          value={`${stats.total_profit_interested.toFixed(0)}€`}
          icon={DollarSign}
          accent="#788bff"
        />
      </div>

      <div
        style={{
          background: "#151b25",
          border: "1px solid rgba(84,101,255,0.15)",
          borderRadius: "12px",
          overflow: "hidden",
        }}
      >
        <div style={{ padding: "14px 20px", borderBottom: "1px solid rgba(84,101,255,0.08)" }}>
          <h3 style={{ fontSize: "13px", fontWeight: 600, color: "#8a97b0" }}>
            Top Suchbegriffe (letzte 7 Tage)
          </h3>
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(84,101,255,0.08)" }}>
              {["#", "Suchbegriff", "Preise"].map((h, i) => (
                <th
                  key={h}
                  style={{
                    textAlign: i === 2 ? "right" : "left",
                    padding: "10px 20px",
                    fontSize: "11px",
                    fontWeight: 500,
                    color: "#4a5568",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stats.top_search_terms.map((t, i) => (
              <tr
                key={t.search_term}
                style={{ borderBottom: "1px solid rgba(84,101,255,0.06)", transition: "background 0.15s ease" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(84,101,255,0.05)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <td style={{ padding: "12px 20px", color: "#4a5568" }}>{i + 1}</td>
                <td style={{ padding: "12px 20px", fontWeight: 500, color: "#f0f4ff" }}>{t.search_term}</td>
                <td style={{ padding: "12px 20px", textAlign: "right", color: "#8a97b0" }}>{t.cnt}</td>
              </tr>
            ))}
            {stats.top_search_terms.length === 0 && (
              <tr>
                <td colSpan={3} style={{ padding: "36px", textAlign: "center", color: "#4a5568" }}>
                  Noch keine Daten
                </td>
              </tr>
            )}
          </tbody>
        </table>

        <div
          style={{
            padding: "12px 20px",
            borderTop: "1px solid rgba(84,101,255,0.08)",
            display: "flex",
            gap: "20px",
            fontSize: "12px",
            color: "#4a5568",
          }}
        >
          <span>Gesamt Alerts: <span style={{ color: "#8a97b0", fontWeight: 500 }}>{stats.total_alerts}</span></span>
          <span>Diese Woche: <span style={{ color: "#8a97b0", fontWeight: 500 }}>{stats.week_alerts}</span></span>
        </div>
      </div>
    </div>
  );
}
