import { useEffect, useState } from "react";
import { Save, Plus, Trash2 } from "lucide-react";
import { api, AppConfig, BlacklistEntry } from "../api";

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
    <div className="flex flex-col gap-1">
      <label className="text-xs text-gray-400">{label}</label>
      <div className="flex items-center gap-2">
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 w-full"
        />
        {unit && <span className="text-xs text-gray-500 flex-shrink-0">{unit}</span>}
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

  const loadConfig = () =>
    api.config.get().then((c) => { setConfig(c); setDraft(c); });
  const loadBlacklist = () =>
    api.blacklist.list().then((r) => setBlacklist(r.blacklist));

  useEffect(() => { loadConfig(); loadBlacklist(); }, []);

  const set = (key: keyof AppConfig, raw: string) => {
    const val =
      typeof config?.[key] === "number" ? (raw === "" ? 0 : Number(raw)) : raw;
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
    setTimeout(() => setSaved(false), 2000);
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

  if (!config || !draft) {
    return <div className="text-center py-16 text-gray-500">Lade Einstellungen…</div>;
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <h2 className="text-xl font-bold mb-6">Einstellungen</h2>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-4">
          <h3 className="text-sm font-semibold text-gray-300">Bot-Parameter</h3>
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Max Budget"
              value={draft.MAX_BUDGET_EUR ?? ""}
              onChange={(v) => set("MAX_BUDGET_EUR", v)}
              unit="€"
            />
            <Field
              label="Min Profit"
              value={draft.MIN_PROFIT_EUR ?? ""}
              onChange={(v) => set("MIN_PROFIT_EUR", v)}
              unit="€"
            />
            <Field
              label="Preis-Threshold"
              value={draft.PRICE_THRESHOLD_PERCENT ?? ""}
              onChange={(v) => set("PRICE_THRESHOLD_PERCENT", v)}
              unit="%"
            />
            <Field
              label="Rolling-Average Zeitraum"
              value={draft.ROLLING_AVERAGE_DAYS ?? ""}
              onChange={(v) => set("ROLLING_AVERAGE_DAYS", v)}
              unit="Tage"
            />
            <Field
              label="Scrape-Interval"
              value={draft.SCRAPE_INTERVAL_MINUTES ?? ""}
              onChange={(v) => set("SCRAPE_INTERVAL_MINUTES", v)}
              unit="Min"
            />
            <Field
              label="Min Fotos"
              value={draft.MIN_LISTING_IMAGES ?? ""}
              onChange={(v) => set("MIN_LISTING_IMAGES", v)}
            />
            <Field
              label="Alert Cooldown"
              value={draft.ALERT_COOLDOWN_HOURS ?? ""}
              onChange={(v) => set("ALERT_COOLDOWN_HOURS", v)}
              unit="Std"
            />
            <Field
              label="Max Seller-Inserate (Händler-Grenze)"
              value={draft.MAX_SELLER_LISTINGS ?? ""}
              onChange={(v) => set("MAX_SELLER_LISTINGS", v)}
            />
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-400">Log Level</label>
              <select
                value={draft.LOG_LEVEL ?? "INFO"}
                onChange={(e) => set("LOG_LEVEL", e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              >
                {["DEBUG", "INFO", "WARNING", "ERROR"].map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex items-center gap-3 mt-2">
            <button
              onClick={handleSave}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg"
            >
              <Save size={14} /> Speichern
            </button>
            {saved && <span className="text-xs text-green-400">✅ Gespeichert</span>}
            {config.scraper_paused && (
              <span className="text-xs text-yellow-400 ml-auto">⏸ Scraper pausiert</span>
            )}
          </div>
        </div>
      </div>

      <div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Blacklist</h3>
          <div className="flex gap-2 mb-4">
            <input
              value={newSeller}
              onChange={(e) => setNewSeller(e.target.value)}
              placeholder="Seller-ID"
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 flex-1"
            />
            <input
              value={newReason}
              onChange={(e) => setNewReason(e.target.value)}
              placeholder="Grund (optional)"
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 flex-1"
            />
            <button
              onClick={handleAddBlacklist}
              className="flex items-center gap-1 bg-red-700 hover:bg-red-800 text-white text-sm px-3 py-2 rounded-lg"
            >
              <Plus size={14} /> Hinzufügen
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {blacklist.map((entry) => (
              <div
                key={entry.seller_id}
                className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2"
              >
                <div>
                  <span className="text-sm text-white font-mono">{entry.seller_id}</span>
                  {entry.reason && (
                    <span className="text-xs text-gray-500 ml-2">{entry.reason}</span>
                  )}
                </div>
                <button
                  onClick={() => handleRemoveBlacklist(entry.seller_id)}
                  className="text-gray-600 hover:text-red-400"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            {blacklist.length === 0 && (
              <p className="text-xs text-gray-600 text-center py-4">Blacklist ist leer</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
