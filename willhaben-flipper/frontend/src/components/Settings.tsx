import { useEffect, useState } from "react";
import { Save, Plus, Trash2 } from "lucide-react";
import { api, AppConfig, BlacklistEntry } from "../api";

const inputStyle: React.CSSProperties = {
  background: "#19212e",
  border: "1px solid rgba(84,101,255,0.2)",
  borderRadius: "8px",
  padding: "8px 12px",
  fontSize: "13px",
  color: "#f0f4ff",
  width: "100%",
  outline: "none",
  transition: "border-color 0.2s ease",
  fontFamily: "inherit",
};

function Field({
  label,
  value,
  onChange,
  type = "number",
  unit,
}: {
  label: string;
  value: string | number;
  onChange: (v: string) => void;
  type?: string;
  unit?: string;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
      <label style={{ fontSize: "11px", fontWeight: 500, color: "#8a97b0", letterSpacing: "0.03em" }}>
        {label}
      </label>
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          style={inputStyle}
          onFocus={(e) => (e.currentTarget.style.borderColor = "#5465ff")}
          onBlur={(e) => (e.currentTarget.style.borderColor = "rgba(84,101,255,0.2)")}
        />
        {unit && (
          <span style={{ fontSize: "12px", color: "#4a5568", flexShrink: 0, minWidth: "28px" }}>
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}

export default function Settings() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [draft, setDraft] = useState<Partial<AppConfig>>({});
  const [saved, setSaved] = useState(false);
  const [blacklist, setBlacklist] = useState<BlacklistEntry[]>([]);
  const [newSeller, setNewSeller] = useState("");
  const [newReason, setNewReason] = useState("");

  const loadConfig = () => api.config.get().then((c) => { setConfig(c); setDraft(c); });
  const loadBlacklist = () => api.blacklist.list().then((r) => setBlacklist(r.blacklist));

  useEffect(() => { loadConfig(); loadBlacklist(); }, []);

  const set = (key: keyof AppConfig, raw: string) => {
    const val = typeof config?.[key] === "number" ? (raw === "" ? 0 : Number(raw)) : raw;
    setDraft((d) => ({ ...d, [key]: val }));
  };

  const handleSave = async () => {
    const updates: Partial<AppConfig> = {};
    for (const k of Object.keys(draft) as (keyof AppConfig)[]) {
      if (k !== "scraper_paused" && draft[k] !== config?.[k]) {
        (updates as Record<string, unknown>)[k] = draft[k];
      }
    }
    await api.config.update(updates);
    setSaved(true);
    loadConfig();
    setTimeout(() => setSaved(false), 2500);
  };

  const handleAddBlacklist = async () => {
    if (!newSeller.trim()) return;
    await api.blacklist.add({ seller_id: newSeller.trim(), reason: newReason || null });
    setNewSeller("");
    setNewReason("");
    loadBlacklist();
  };

  const handleRemoveBlacklist = async (id: string) => {
    await api.blacklist.remove(id);
    loadBlacklist();
  };

  if (!config) {
    return (
      <div style={{ textAlign: "center", padding: "64px 0", color: "#4a5568" }}>
        <div className="pulse" style={{ fontSize: "13px" }}>Lade Einstellungen…</div>
      </div>
    );
  }

  const sectionStyle: React.CSSProperties = {
    background: "#151b25",
    border: "1px solid rgba(84,101,255,0.15)",
    borderRadius: "12px",
    padding: "20px",
  };

  const sectionTitle: React.CSSProperties = {
    fontSize: "13px",
    fontWeight: 600,
    color: "#8a97b0",
    marginBottom: "18px",
    letterSpacing: "0.03em",
  };

  return (
    <div style={{ maxWidth: "640px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "24px" }}>
      <h2 style={{ fontSize: "20px", fontWeight: 700, color: "#f0f4ff" }}>Einstellungen</h2>

      {/* Bot parameters */}
      <div style={sectionStyle}>
        <p style={sectionTitle}>Bot-Parameter</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
          <Field label="Max Budget" value={draft.MAX_BUDGET_EUR ?? ""} onChange={(v) => set("MAX_BUDGET_EUR", v)} unit="€" />
          <Field label="Min Profit" value={draft.MIN_PROFIT_EUR ?? ""} onChange={(v) => set("MIN_PROFIT_EUR", v)} unit="€" />
          <Field label="Preis-Threshold" value={draft.PRICE_THRESHOLD_PERCENT ?? ""} onChange={(v) => set("PRICE_THRESHOLD_PERCENT", v)} unit="%" />
          <Field label="Rolling-Average Zeitraum" value={draft.ROLLING_AVERAGE_DAYS ?? ""} onChange={(v) => set("ROLLING_AVERAGE_DAYS", v)} unit="Tage" />
          <Field label="Scrape-Interval" value={draft.SCRAPE_INTERVAL_MINUTES ?? ""} onChange={(v) => set("SCRAPE_INTERVAL_MINUTES", v)} unit="Min" />
          <Field label="Min Fotos" value={draft.MIN_LISTING_IMAGES ?? ""} onChange={(v) => set("MIN_LISTING_IMAGES", v)} />
          <Field label="Alert Cooldown" value={draft.ALERT_COOLDOWN_HOURS ?? ""} onChange={(v) => set("ALERT_COOLDOWN_HOURS", v)} unit="Std" />
          <Field label="Max Seller-Inserate" value={draft.MAX_SELLER_LISTINGS ?? ""} onChange={(v) => set("MAX_SELLER_LISTINGS", v)} />
          <div style={{ display: "flex", flexDirection: "column", gap: "5px", gridColumn: "1 / -1" }}>
            <label style={{ fontSize: "11px", fontWeight: 500, color: "#8a97b0", letterSpacing: "0.03em" }}>
              Log Level
            </label>
            <select
              value={draft.LOG_LEVEL ?? "INFO"}
              onChange={(e) => set("LOG_LEVEL", e.target.value)}
              style={{ ...inputStyle, cursor: "pointer" }}
              onFocus={(e) => (e.currentTarget.style.borderColor = "#5465ff")}
              onBlur={(e) => (e.currentTarget.style.borderColor = "rgba(84,101,255,0.2)")}
            >
              {["DEBUG", "INFO", "WARNING", "ERROR"].map((l) => (
                <option key={l} value={l} style={{ background: "#19212e" }}>{l}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginTop: "20px" }}>
          <button
            onClick={handleSave}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "7px",
              fontSize: "13px",
              fontWeight: 600,
              color: "#f0f4ff",
              background: "#5465ff",
              border: "none",
              padding: "9px 18px",
              borderRadius: "8px",
              transition: "background 0.2s ease",
              cursor: "pointer",
              fontFamily: "inherit",
              outline: "none",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#788bff")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#5465ff")}
          >
            <Save size={14} /> Speichern
          </button>
          {saved && (
            <span style={{ fontSize: "12px", color: "#22d3a5", fontWeight: 500 }}>
              ✓ Gespeichert
            </span>
          )}
          {config.scraper_paused && (
            <span style={{ fontSize: "12px", color: "#f59e0b", marginLeft: "auto" }}>
              ⏸ Scraper pausiert
            </span>
          )}
        </div>
      </div>

      {/* Blacklist */}
      <div style={sectionStyle}>
        <p style={sectionTitle}>Blacklist</p>
        <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
          <input
            value={newSeller}
            onChange={(e) => setNewSeller(e.target.value)}
            placeholder="Seller-ID"
            style={{ ...inputStyle, flex: 1 }}
            onFocus={(e) => (e.currentTarget.style.borderColor = "#5465ff")}
            onBlur={(e) => (e.currentTarget.style.borderColor = "rgba(84,101,255,0.2)")}
            onKeyDown={(e) => e.key === "Enter" && handleAddBlacklist()}
          />
          <input
            value={newReason}
            onChange={(e) => setNewReason(e.target.value)}
            placeholder="Grund (optional)"
            style={{ ...inputStyle, flex: 1 }}
            onFocus={(e) => (e.currentTarget.style.borderColor = "#5465ff")}
            onBlur={(e) => (e.currentTarget.style.borderColor = "rgba(84,101,255,0.2)")}
            onKeyDown={(e) => e.key === "Enter" && handleAddBlacklist()}
          />
          <button
            onClick={handleAddBlacklist}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              fontSize: "12px",
              fontWeight: 600,
              color: "#f0f4ff",
              background: "#ef4444",
              border: "none",
              padding: "8px 14px",
              borderRadius: "8px",
              transition: "background 0.2s ease",
              cursor: "pointer",
              fontFamily: "inherit",
              outline: "none",
              flexShrink: 0,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#dc2626")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#ef4444")}
          >
            <Plus size={14} /> Hinzufügen
          </button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {blacklist.map((entry) => (
            <div
              key={entry.seller_id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                background: "#19212e",
                borderRadius: "8px",
                padding: "10px 14px",
                border: "1px solid rgba(84,101,255,0.1)",
              }}
            >
              <div>
                <span style={{ fontSize: "13px", fontWeight: 500, color: "#f0f4ff", fontFamily: "monospace" }}>
                  {entry.seller_id}
                </span>
                {entry.reason && (
                  <span style={{ fontSize: "12px", color: "#4a5568", marginLeft: "10px" }}>
                    {entry.reason}
                  </span>
                )}
              </div>
              <button
                onClick={() => handleRemoveBlacklist(entry.seller_id)}
                style={{
                  color: "#4a5568",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: "2px",
                  display: "flex",
                  transition: "color 0.15s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#ef4444")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "#4a5568")}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          {blacklist.length === 0 && (
            <p style={{ fontSize: "12px", color: "#4a5568", textAlign: "center", padding: "20px 0" }}>
              Blacklist ist leer
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
