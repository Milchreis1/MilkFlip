import { useEffect, useState, useCallback } from "react";
import { ExternalLink, CheckCircle, XCircle, Clock, Image } from "lucide-react";
import { api, Alert } from "../api";

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 70 ? "bg-green-500" : score >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <span className={`${color} text-white text-xs font-bold px-2 py-0.5 rounded-full`}>
      {score}/100
    </span>
  );
}

function formatAge(minutes: number | null): string {
  if (minutes === null) return "";
  if (minutes < 60) return `Vor ${Math.round(minutes)} Min`;
  return `Vor ${Math.round(minutes / 60)} Std`;
}

function AlertCard({ alert, onAction }: { alert: Alert; onAction: () => void }) {
  const handleAction = async (action: string) => {
    await api.alerts.updateAction(alert.id, action);
    onAction();
  };

  return (
    <div
      className={`bg-gray-900 border rounded-xl p-4 flex flex-col gap-3 ${
        alert.user_action === "interested"
          ? "border-green-700"
          : alert.user_action === "skipped"
          ? "border-gray-700 opacity-60"
          : "border-gray-800"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <ScoreBadge score={alert.score} />
            {alert.age_minutes !== null && alert.age_minutes < 120 && (
              <span className="text-xs text-blue-400 flex items-center gap-1">
                <Clock size={11} /> Neu
              </span>
            )}
          </div>
          <p className="font-semibold text-white leading-snug line-clamp-2">
            {alert.title}
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-xl font-bold text-white">{alert.price.toFixed(0)}€</p>
          <p className="text-xs text-red-400 font-medium">
            -{alert.price_delta_percent.toFixed(0)}% unter Avg
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-400">
        <span>📊 Durchschnitt: {alert.rolling_average.toFixed(0)}€</span>
        <span>💰 Profit: ~{alert.expected_profit.toFixed(0)}€</span>
        {alert.location && <span>📍 {alert.location}</span>}
        <span className="flex items-center gap-1">
          <Image size={11} /> {alert.images_count} Fotos
        </span>
        {alert.age_minutes !== null && (
          <span className="flex items-center gap-1">
            <Clock size={11} /> {formatAge(alert.age_minutes)}
          </span>
        )}
        <span className="text-gray-600">
          {new Date(alert.alerted_at).toLocaleString("de-AT")}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <a
          href={alert.url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 bg-gray-800 hover:bg-gray-750 px-3 py-1.5 rounded-lg flex-1 justify-center transition-colors"
        >
          <ExternalLink size={13} /> Zum Inserat
        </a>
        {!alert.user_action && (
          <>
            <button
              onClick={() => handleAction("interested")}
              className="flex items-center gap-1 text-xs text-green-400 hover:text-green-300 bg-gray-800 hover:bg-gray-750 px-3 py-1.5 rounded-lg transition-colors"
            >
              <CheckCircle size={13} /> Interessiert
            </button>
            <button
              onClick={() => handleAction("skipped")}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 bg-gray-800 hover:bg-gray-750 px-3 py-1.5 rounded-lg transition-colors"
            >
              <XCircle size={13} /> Skip
            </button>
          </>
        )}
        {alert.user_action === "interested" && (
          <span className="text-xs text-green-500 font-medium">✅ Interessiert</span>
        )}
        {alert.user_action === "skipped" && (
          <span className="text-xs text-gray-500 font-medium">❌ Übersprungen</span>
        )}
      </div>
    </div>
  );
}

type SortKey = "score" | "alerted_at" | "expected_profit";

export default function AlertFeed() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [minScore, setMinScore] = useState(0);
  const [sortKey, setSortKey] = useState<SortKey>("alerted_at");
  const [showUnseen, setShowUnseen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.alerts.list({
        page,
        page_size: 20,
        min_score: minScore > 0 ? minScore : undefined,
        user_action: showUnseen ? undefined : undefined,
      });
      setAlerts(res.alerts);
    } finally {
      setLoading(false);
    }
  }, [page, minScore, showUnseen]);

  useEffect(() => { load(); }, [load]);

  const sorted = [...alerts].sort((a, b) => {
    if (sortKey === "score") return b.score - a.score;
    if (sortKey === "expected_profit") return b.expected_profit - a.expected_profit;
    return new Date(b.alerted_at).getTime() - new Date(a.alerted_at).getTime();
  });

  const filtered = showUnseen ? sorted.filter((a) => !a.user_action) : sorted;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Alert Feed</h2>
        <button
          onClick={load}
          className="text-xs text-blue-400 hover:text-blue-300 bg-gray-800 px-3 py-1.5 rounded-lg"
        >
          Aktualisieren
        </button>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-4 flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Min Score</label>
          <input
            type="range"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => { setMinScore(Number(e.target.value)); setPage(0); }}
            className="w-28"
          />
          <span className="text-xs font-mono text-white w-8">{minScore}</span>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Sortierung</label>
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            className="bg-gray-800 text-white text-xs rounded px-2 py-1 border border-gray-700"
          >
            <option value="alerted_at">Datum</option>
            <option value="score">Score</option>
            <option value="expected_profit">Profit</option>
          </select>
        </div>

        <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={showUnseen}
            onChange={(e) => setShowUnseen(e.target.checked)}
            className="rounded"
          />
          Nur ungesehene
        </label>
      </div>

      {loading && (
        <div className="text-center py-12 text-gray-500">Lade Alerts…</div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          Keine Alerts gefunden. Der Bot läuft und sammelt Daten…
        </div>
      )}

      <div className="flex flex-col gap-3">
        {filtered.map((alert) => (
          <AlertCard key={alert.id} alert={alert} onAction={load} />
        ))}
      </div>

      <div className="flex justify-between mt-6">
        <button
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
          className="text-xs text-gray-400 disabled:opacity-30 bg-gray-800 px-4 py-2 rounded-lg"
        >
          ← Zurück
        </button>
        <span className="text-xs text-gray-500 self-center">Seite {page + 1}</span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={alerts.length < 20}
          className="text-xs text-gray-400 disabled:opacity-30 bg-gray-800 px-4 py-2 rounded-lg"
        >
          Weiter →
        </button>
      </div>
    </div>
  );
}
