import { useEffect, useState, useCallback } from "react";
import { ExternalLink, CheckCircle, XCircle, Clock, ImageIcon } from "lucide-react";
import { api, Alert } from "../api";

const S = {
  card: (interested: boolean, skipped: boolean): React.CSSProperties => ({
    background: "#151b25",
    border: `1px solid ${interested ? "rgba(34,211,165,0.25)" : skipped ? "rgba(84,101,255,0.06)" : "rgba(84,101,255,0.15)"}`,
    borderRadius: "12px",
    padding: "16px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    opacity: skipped ? 0.5 : 1,
    transition: "all 0.2s ease",
  }),
  btn: (color: string, border: string): React.CSSProperties => ({
    display: "flex",
    alignItems: "center",
    gap: "5px",
    fontSize: "12px",
    fontWeight: 500,
    color,
    background: "transparent",
    border: `1px solid ${border}`,
    padding: "7px 12px",
    borderRadius: "8px",
    transition: "all 0.2s ease",
    cursor: "pointer",
    outline: "none",
    fontFamily: "inherit",
  }),
};

function ScoreBadge({ score }: { score: number }) {
  const [bg, color] =
    score >= 70
      ? ["rgba(34,211,165,0.12)", "#22d3a5"]
      : score >= 40
      ? ["rgba(245,158,11,0.12)", "#f59e0b"]
      : ["rgba(239,68,68,0.12)", "#ef4444"];
  return (
    <span
      style={{
        background: bg,
        color,
        fontSize: "11px",
        fontWeight: 700,
        padding: "3px 9px",
        borderRadius: "20px",
        letterSpacing: "0.02em",
      }}
    >
      {score}/100
    </span>
  );
}

function formatAge(minutes: number | null): string {
  if (minutes === null) return "";
  if (minutes < 60) return `${Math.round(minutes)} Min`;
  return `${Math.round(minutes / 60)} Std`;
}

function AlertCard({ alert, onAction }: { alert: Alert; onAction: () => void }) {
  const interested = alert.user_action === "interested";
  const skipped = alert.user_action === "skipped";

  const handleAction = async (action: string) => {
    await api.alerts.updateAction(alert.id, action);
    onAction();
  };

  return (
    <div style={S.card(interested, skipped)}>
      {/* Top row: badges + title / price */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "12px" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              flexWrap: "wrap",
              marginBottom: "7px",
            }}
          >
            <ScoreBadge score={alert.score} />
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "11px",
                color: "#22d3a5",
                fontWeight: 500,
              }}
            >
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  background: "#22d3a5",
                  display: "inline-block",
                  flexShrink: 0,
                }}
              />
              Aktiv
            </span>
            {alert.age_minutes !== null && alert.age_minutes < 120 && (
              <span
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  fontSize: "11px",
                  color: "#5465ff",
                }}
              >
                <Clock size={10} /> Neu
              </span>
            )}
          </div>
          <p
            style={{
              fontSize: "14px",
              fontWeight: 600,
              color: "#f0f4ff",
              lineHeight: "1.4",
              overflow: "hidden",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
            }}
          >
            {alert.title}
          </p>
        </div>

        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <p style={{ fontSize: "22px", fontWeight: 700, color: "#f0f4ff", lineHeight: 1 }}>
            {alert.price.toFixed(0)}€
          </p>
          <p style={{ fontSize: "11px", color: "#5465ff", fontWeight: 600, marginTop: "3px" }}>
            -{alert.price_delta_percent.toFixed(0)}% unter Ø
          </p>
        </div>
      </div>

      {/* Stats grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "5px 16px" }}>
        <span style={{ fontSize: "12px", color: "#8a97b0" }}>
          Ø{" "}
          <span style={{ color: "#f0f4ff", fontWeight: 500 }}>
            {alert.rolling_average.toFixed(0)}€
          </span>
        </span>
        <span style={{ fontSize: "12px", color: "#22d3a5", fontWeight: 600 }}>
          +{alert.expected_profit.toFixed(0)}€ Profit
        </span>
        {alert.location && (
          <span style={{ fontSize: "12px", color: "#8a97b0" }}>📍 {alert.location}</span>
        )}
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "4px",
            fontSize: "12px",
            color: "#8a97b0",
          }}
        >
          <ImageIcon size={11} />
          {alert.images_count} Fotos
          {alert.age_minutes !== null && (
            <>
              {" "}·{" "}
              <Clock size={10} />
              {formatAge(alert.age_minutes)}
            </>
          )}
        </span>
        <span style={{ fontSize: "11px", color: "#4a5568", gridColumn: "1 / -1" }}>
          {new Date(alert.alerted_at).toLocaleString("de-AT")}
        </span>
      </div>

      {/* Actions */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <a
          href={alert.url}
          target="_blank"
          rel="noreferrer"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "6px",
            fontSize: "12px",
            fontWeight: 600,
            color: "#f0f4ff",
            background: "#5465ff",
            padding: "8px 14px",
            borderRadius: "8px",
            flex: 1,
            transition: "background 0.2s ease",
            textDecoration: "none",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#788bff")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "#5465ff")}
        >
          <ExternalLink size={12} /> Zum Inserat →
        </a>

        {!alert.user_action && (
          <>
            <button
              onClick={() => handleAction("interested")}
              style={S.btn("#22d3a5", "rgba(34,211,165,0.3)")}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(34,211,165,0.1)";
                e.currentTarget.style.borderColor = "#22d3a5";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.borderColor = "rgba(34,211,165,0.3)";
              }}
            >
              <CheckCircle size={12} /> Interessiert
            </button>
            <button
              onClick={() => handleAction("skipped")}
              style={S.btn("#4a5568", "rgba(74,85,104,0.3)")}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "#8a97b0";
                e.currentTarget.style.borderColor = "rgba(138,151,176,0.3)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "#4a5568";
                e.currentTarget.style.borderColor = "rgba(74,85,104,0.3)";
              }}
            >
              <XCircle size={12} /> Skip
            </button>
          </>
        )}
        {interested && (
          <span style={{ fontSize: "12px", color: "#22d3a5", fontWeight: 500 }}>
            ✅ Interessiert
          </span>
        )}
        {skipped && (
          <span style={{ fontSize: "12px", color: "#4a5568", fontWeight: 500 }}>
            ❌ Übersprungen
          </span>
        )}
      </div>
    </div>
  );
}

type SortKey = "score" | "alerted_at" | "expected_profit";

const inputStyle: React.CSSProperties = {
  background: "#19212e",
  color: "#f0f4ff",
  fontSize: "12px",
  border: "1px solid rgba(84,101,255,0.2)",
  borderRadius: "8px",
  padding: "6px 10px",
  outline: "none",
  fontFamily: "inherit",
};

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
      });
      setAlerts(res.alerts);
    } finally {
      setLoading(false);
    }
  }, [page, minScore]);

  useEffect(() => {
    load();
  }, [load]);

  const sorted = [...alerts].sort((a, b) => {
    if (sortKey === "score") return b.score - a.score;
    if (sortKey === "expected_profit") return b.expected_profit - a.expected_profit;
    return new Date(b.alerted_at).getTime() - new Date(a.alerted_at).getTime();
  });

  const filtered = showUnseen ? sorted.filter((a) => !a.user_action) : sorted;

  return (
    <div style={{ maxWidth: "760px", margin: "0 auto" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "24px",
        }}
      >
        <h2 style={{ fontSize: "20px", fontWeight: 700, color: "#f0f4ff" }}>Alert Feed</h2>
        <button
          onClick={load}
          style={{
            fontSize: "12px",
            fontWeight: 500,
            color: "#5465ff",
            background: "transparent",
            border: "1px solid rgba(84,101,255,0.3)",
            padding: "6px 14px",
            borderRadius: "8px",
            transition: "all 0.2s ease",
            cursor: "pointer",
            outline: "none",
            fontFamily: "inherit",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(84,101,255,0.1)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        >
          Aktualisieren
        </button>
      </div>

      {/* Filters */}
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
          <label style={{ fontSize: "12px", color: "#8a97b0" }}>Min Score</label>
          <input
            type="range"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => {
              setMinScore(Number(e.target.value));
              setPage(0);
            }}
            style={{ width: "100px", accentColor: "#5465ff" }}
          />
          <span
            style={{
              fontSize: "12px",
              fontFamily: "monospace",
              color: "#f0f4ff",
              minWidth: "28px",
            }}
          >
            {minScore}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label style={{ fontSize: "12px", color: "#8a97b0" }}>Sortierung</label>
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            style={inputStyle}
          >
            <option value="alerted_at">Datum</option>
            <option value="score">Score</option>
            <option value="expected_profit">Profit</option>
          </select>
        </div>

        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "12px",
            color: "#8a97b0",
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={showUnseen}
            onChange={(e) => setShowUnseen(e.target.checked)}
            style={{ accentColor: "#5465ff" }}
          />
          Nur ungesehene
        </label>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: "center", padding: "64px 0", color: "#4a5568" }}>
          <div className="pulse" style={{ fontSize: "13px" }}>
            Lade Alerts…
          </div>
        </div>
      )}

      {/* Empty */}
      {!loading && filtered.length === 0 && (
        <div style={{ textAlign: "center", padding: "64px 0" }}>
          <p style={{ fontSize: "36px", marginBottom: "14px" }}>🔍</p>
          <p style={{ fontSize: "14px", color: "#4a5568" }}>
            Keine Alerts gefunden. Der Bot läuft und sammelt Daten…
          </p>
        </div>
      )}

      {/* Cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {filtered.map((alert) => (
          <AlertCard key={alert.id} alert={alert} onAction={load} />
        ))}
      </div>

      {/* Pagination */}
      {alerts.length > 0 && (
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "24px" }}>
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            style={{
              fontSize: "12px",
              color: page === 0 ? "#4a5568" : "#8a97b0",
              background: "#151b25",
              border: "1px solid rgba(84,101,255,0.15)",
              padding: "8px 18px",
              borderRadius: "8px",
              cursor: page === 0 ? "default" : "pointer",
              fontFamily: "inherit",
              outline: "none",
            }}
          >
            ← Zurück
          </button>
          <span style={{ fontSize: "12px", color: "#4a5568", alignSelf: "center" }}>
            Seite {page + 1}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={alerts.length < 20}
            style={{
              fontSize: "12px",
              color: alerts.length < 20 ? "#4a5568" : "#8a97b0",
              background: "#151b25",
              border: "1px solid rgba(84,101,255,0.15)",
              padding: "8px 18px",
              borderRadius: "8px",
              cursor: alerts.length < 20 ? "default" : "pointer",
              fontFamily: "inherit",
              outline: "none",
            }}
          >
            Weiter →
          </button>
        </div>
      )}
    </div>
  );
}
