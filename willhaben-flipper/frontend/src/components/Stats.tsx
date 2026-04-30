import { useEffect, useState } from "react";
import { Eye, Bell, TrendingUp, DollarSign, LucideIcon } from "lucide-react";
import { api, StatsData } from "../api";

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  color: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-center gap-4">
      <div className={`${color} rounded-lg p-2.5`}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value}</p>
        <p className="text-xs text-gray-400">{label}</p>
      </div>
    </div>
  );
}

export default function Stats() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.stats.get().then((s) => { setStats(s); setLoading(false); });
  }, []);

  if (loading) {
    return <div className="text-center py-16 text-gray-500">Lade Stats…</div>;
  }
  if (!stats) return null;

  return (
    <div className="max-w-3xl mx-auto">
      <h2 className="text-xl font-bold mb-6">Statistiken</h2>

      <div className="grid grid-cols-2 gap-4 mb-8">
        <MetricCard
          label="Heute gesehen"
          value={stats.today_seen.toLocaleString()}
          icon={Eye}
          color="bg-blue-600"
        />
        <MetricCard
          label="Heute Alerts"
          value={stats.today_alerts.toLocaleString()}
          icon={Bell}
          color="bg-yellow-600"
        />
        <MetricCard
          label="Beste Marge heute"
          value={stats.best_margin_today != null ? `${stats.best_margin_today.toFixed(0)}€` : "—"}
          icon={TrendingUp}
          color="bg-green-600"
        />
        <MetricCard
          label="Gesamtgewinn (Interessiert)"
          value={`${stats.total_profit_interested.toFixed(0)}€`}
          icon={DollarSign}
          color="bg-purple-600"
        />
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-800">
          <h3 className="text-sm font-semibold text-gray-300">
            Top Suchbegriffe (letzte 7 Tage)
          </h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-500 border-b border-gray-800">
              <th className="text-left px-5 py-3">#</th>
              <th className="text-left px-5 py-3">Suchbegriff</th>
              <th className="text-right px-5 py-3">Preise gesammelt</th>
            </tr>
          </thead>
          <tbody>
            {stats.top_search_terms.map((t, i) => (
              <tr key={t.search_term} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="px-5 py-3 text-gray-500">{i + 1}</td>
                <td className="px-5 py-3 font-medium text-white">{t.search_term}</td>
                <td className="px-5 py-3 text-right text-gray-400">{t.cnt}</td>
              </tr>
            ))}
            {stats.top_search_terms.length === 0 && (
              <tr>
                <td colSpan={3} className="px-5 py-8 text-center text-gray-600">
                  Noch keine Daten
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <div className="px-5 py-3 border-t border-gray-800 flex gap-6 text-xs text-gray-500">
          <span>Gesamt Alerts: {stats.total_alerts}</span>
          <span>Diese Woche: {stats.week_alerts}</span>
        </div>
      </div>
    </div>
  );
}
