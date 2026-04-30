import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { api, PriceHistoryEntry, SearchProfile } from "../api";

interface ChartPoint {
  date: string;
  price: number;
  avg?: number;
}

function computeRollingAvg(history: PriceHistoryEntry[]): ChartPoint[] {
  if (history.length === 0) return [];
  const window = 10;
  return history.map((entry, i) => {
    const slice = history.slice(Math.max(0, i - window + 1), i + 1);
    const avg = slice.reduce((s, h) => s + h.price, 0) / slice.length;
    return {
      date: new Date(entry.seen_at).toLocaleDateString("de-AT"),
      price: Math.round(entry.price),
      avg: Math.round(avg),
    };
  });
}

export default function PriceChart() {
  const [profiles, setProfiles] = useState<SearchProfile[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [days, setDays] = useState(30);
  const [data, setData] = useState<ChartPoint[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.profiles.list().then((res) => {
      setProfiles(res.profiles);
      if (res.profiles.length > 0) setSelected(res.profiles[0].query);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    api.priceHistory.get(selected, days).then((res) => {
      setData(computeRollingAvg(res.history));
      setLoading(false);
    });
  }, [selected, days]);

  const btnStyle = (active: boolean): React.CSSProperties => ({
    fontSize: "12px",
    fontWeight: 500,
    padding: "6px 14px",
    borderRadius: "8px",
    border: active ? "none" : "1px solid rgba(84,101,255,0.2)",
    background: active ? "#5465ff" : "transparent",
    color: active ? "#f0f4ff" : "#8a97b0",
    cursor: "pointer",
    transition: "all 0.15s ease",
    fontFamily: "inherit",
    outline: "none",
  });

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto" }}>
      <h2 style={{ fontSize: "20px", fontWeight: 700, color: "#f0f4ff", marginBottom: "24px" }}>
        Preishistorie
      </h2>

      {/* Controls */}
      <div
        style={{
          background: "#151b25",
          border: "1px solid rgba(84,101,255,0.15)",
          borderRadius: "12px",
          padding: "14px 18px",
          marginBottom: "16px",
          display: "flex",
          flexWrap: "wrap",
          gap: "16px",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <label style={{ fontSize: "12px", color: "#8a97b0" }}>Suchprofil</label>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            style={{
              background: "#19212e",
              color: "#f0f4ff",
              fontSize: "12px",
              border: "1px solid rgba(84,101,255,0.2)",
              borderRadius: "8px",
              padding: "6px 10px",
              outline: "none",
              fontFamily: "inherit",
              cursor: "pointer",
            }}
          >
            {profiles.map((p) => (
              <option key={p.id} value={p.query} style={{ background: "#19212e" }}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <label style={{ fontSize: "12px", color: "#8a97b0", marginRight: "4px" }}>Zeitraum</label>
          {[7, 14, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              style={btnStyle(days === d)}
              onMouseEnter={(e) => {
                if (days !== d) e.currentTarget.style.color = "#f0f4ff";
              }}
              onMouseLeave={(e) => {
                if (days !== d) e.currentTarget.style.color = "#8a97b0";
              }}
            >
              {d}T
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: "center", padding: "64px 0", color: "#4a5568" }}>
          <div className="pulse" style={{ fontSize: "13px" }}>Lade Daten…</div>
        </div>
      )}

      {/* Empty */}
      {!loading && data.length === 0 && (
        <div style={{ textAlign: "center", padding: "64px 0" }}>
          <p style={{ fontSize: "36px", marginBottom: "14px" }}>📈</p>
          <p style={{ fontSize: "13px", color: "#4a5568" }}>
            Noch keine Preisdaten für „{selected}". Warte auf den ersten Scrape-Zyklus.
          </p>
        </div>
      )}

      {/* Chart */}
      {!loading && data.length > 0 && (
        <div
          style={{
            background: "#151b25",
            border: "1px solid rgba(84,101,255,0.15)",
            borderRadius: "12px",
            padding: "20px 16px 12px",
          }}
        >
          <ResponsiveContainer width="100%" height={380}>
            <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(84,101,255,0.08)" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "#4a5568" }}
                tickLine={false}
                axisLine={{ stroke: "rgba(84,101,255,0.1)" }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#4a5568" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}€`}
                width={58}
              />
              <Tooltip
                contentStyle={{
                  background: "#19212e",
                  border: "1px solid rgba(84,101,255,0.2)",
                  borderRadius: "10px",
                  color: "#f0f4ff",
                  fontSize: 12,
                  fontFamily: "Satoshi, Inter, sans-serif",
                }}
                formatter={(v: number) => [`${v}€`]}
                labelStyle={{ color: "#8a97b0", marginBottom: "4px" }}
              />
              <Legend
                wrapperStyle={{ fontSize: 12, color: "#8a97b0", paddingTop: "12px" }}
              />
              <Line
                type="monotone"
                dataKey="price"
                name="Preis"
                stroke="#5465ff"
                dot={false}
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="avg"
                name="Rolling Avg"
                stroke="#f59e0b"
                dot={false}
                strokeWidth={2}
                strokeDasharray="5 5"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
