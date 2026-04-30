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

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-xl font-bold mb-6">Preishistorie</h2>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6 flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Suchprofil</label>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="bg-gray-800 text-white text-sm rounded px-2 py-1 border border-gray-700"
          >
            {profiles.map((p) => (
              <option key={p.id} value={p.query}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Zeitraum</label>
          {[7, 14, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`text-xs px-3 py-1 rounded-lg ${
                days === d
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {d}T
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="text-center py-16 text-gray-500">Lade Daten…</div>
      )}

      {!loading && data.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          Noch keine Preisdaten für „{selected}". Warte auf den ersten Scrape-Zyklus.
        </div>
      )}

      {!loading && data.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <ResponsiveContainer width="100%" height={380}>
            <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "#9ca3af" }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#9ca3af" }}
                tickLine={false}
                tickFormatter={(v) => `${v}€`}
                width={60}
              />
              <Tooltip
                contentStyle={{
                  background: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: 8,
                  color: "#f9fafb",
                  fontSize: 12,
                }}
                formatter={(v: number) => [`${v}€`]}
              />
              <Legend
                wrapperStyle={{ fontSize: 12, color: "#9ca3af" }}
              />
              <Line
                type="monotone"
                dataKey="price"
                name="Preis"
                stroke="#60a5fa"
                dot={false}
                strokeWidth={1.5}
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
