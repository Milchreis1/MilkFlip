import { useEffect, useState } from "react";
import { Plus, Trash2, ToggleLeft, ToggleRight } from "lucide-react";
import { api, SearchProfile } from "../api";

const EMPTY: Omit<SearchProfile, "id"> = {
  name: "",
  query: "",
  category_id: null,
  max_price: null,
  min_price: null,
  active: true,
  custom_threshold: null,
};

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

export default function SearchProfiles() {
  const [profiles, setProfiles] = useState<SearchProfile[]>([]);
  const [form, setForm] = useState<Omit<SearchProfile, "id">>(EMPTY);
  const [showForm, setShowForm] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const load = () => api.profiles.list().then((res) => setProfiles(res.profiles));

  useEffect(() => { load(); }, []);

  const handleToggle = async (p: SearchProfile) => {
    await api.profiles.update(p.id!, { active: !p.active });
    load();
  };

  const handleDelete = async (id: number) => {
    await api.profiles.delete(id);
    setConfirmDelete(null);
    load();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.query) return;
    setSaving(true);
    try {
      await api.profiles.create(form);
      setForm(EMPTY);
      setShowForm(false);
      load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: "680px", margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 700, color: "#f0f4ff" }}>Suchprofile</h2>
        <button
          onClick={() => setShowForm((v) => !v)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "7px",
            fontSize: "13px",
            fontWeight: 600,
            color: "#f0f4ff",
            background: "#5465ff",
            border: "none",
            padding: "8px 16px",
            borderRadius: "8px",
            transition: "background 0.2s ease",
            cursor: "pointer",
            fontFamily: "inherit",
            outline: "none",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#788bff")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "#5465ff")}
        >
          <Plus size={15} /> Neu
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          style={{
            background: "#151b25",
            border: "1px solid rgba(84,101,255,0.2)",
            borderRadius: "12px",
            padding: "20px",
            marginBottom: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          <p style={{ fontSize: "13px", fontWeight: 600, color: "#8a97b0" }}>Neues Profil</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            {[
              { label: "Name *", key: "name", placeholder: "Nintendo Switch" },
              { label: "Suchbegriff *", key: "query", placeholder: "Nintendo Switch OLED" },
            ].map(({ label, key, placeholder }) => (
              <div key={key} style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                <label style={{ fontSize: "11px", fontWeight: 500, color: "#8a97b0" }}>{label}</label>
                <input
                  required={key === "name" || key === "query"}
                  value={(form as Record<string, unknown>)[key] as string}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  placeholder={placeholder}
                  style={inputStyle}
                  onFocus={(e) => (e.currentTarget.style.borderColor = "#5465ff")}
                  onBlur={(e) => (e.currentTarget.style.borderColor = "rgba(84,101,255,0.2)")}
                />
              </div>
            ))}
            {[
              { label: "Min Preis (€)", key: "min_price", placeholder: "0" },
              { label: "Max Preis (€)", key: "max_price", placeholder: "500" },
              { label: "Threshold % (optional)", key: "custom_threshold", placeholder: "35" },
            ].map(({ label, key, placeholder }) => (
              <div key={key} style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                <label style={{ fontSize: "11px", fontWeight: 500, color: "#8a97b0" }}>{label}</label>
                <input
                  type="number"
                  value={(form as Record<string, unknown>)[key] as string ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, [key]: e.target.value ? Number(e.target.value) : null })
                  }
                  placeholder={placeholder}
                  style={inputStyle}
                  onFocus={(e) => (e.currentTarget.style.borderColor = "#5465ff")}
                  onBlur={(e) => (e.currentTarget.style.borderColor = "rgba(84,101,255,0.2)")}
                />
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              style={{
                fontSize: "13px",
                fontWeight: 500,
                color: "#8a97b0",
                background: "transparent",
                border: "1px solid rgba(84,101,255,0.2)",
                padding: "8px 16px",
                borderRadius: "8px",
                cursor: "pointer",
                fontFamily: "inherit",
                outline: "none",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = "#f0f4ff"; e.currentTarget.style.borderColor = "rgba(84,101,255,0.4)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = "#8a97b0"; e.currentTarget.style.borderColor = "rgba(84,101,255,0.2)"; }}
            >
              Abbrechen
            </button>
            <button
              type="submit"
              disabled={saving}
              style={{
                fontSize: "13px",
                fontWeight: 600,
                color: "#f0f4ff",
                background: saving ? "#4a5568" : "#5465ff",
                border: "none",
                padding: "8px 18px",
                borderRadius: "8px",
                cursor: saving ? "default" : "pointer",
                fontFamily: "inherit",
                outline: "none",
                transition: "background 0.2s ease",
              }}
              onMouseEnter={(e) => { if (!saving) e.currentTarget.style.background = "#788bff"; }}
              onMouseLeave={(e) => { if (!saving) e.currentTarget.style.background = "#5465ff"; }}
            >
              {saving ? "Speichern…" : "Speichern"}
            </button>
          </div>
        </form>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {profiles.map((p) => (
          <div
            key={p.id}
            style={{
              background: "#151b25",
              border: "1px solid rgba(84,101,255,0.15)",
              borderRadius: "12px",
              padding: "14px 16px",
              display: "flex",
              alignItems: "center",
              gap: "14px",
              transition: "border-color 0.2s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(84,101,255,0.3)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "rgba(84,101,255,0.15)")}
          >
            <button
              onClick={() => handleToggle(p)}
              style={{
                color: p.active ? "#22d3a5" : "#4a5568",
                background: "none",
                border: "none",
                cursor: "pointer",
                display: "flex",
                padding: 0,
                transition: "color 0.15s ease",
                flexShrink: 0,
              }}
              title={p.active ? "Deaktivieren" : "Aktivieren"}
            >
              {p.active ? <ToggleRight size={24} /> : <ToggleLeft size={24} />}
            </button>

            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontSize: "14px", fontWeight: 600, color: "#f0f4ff" }}>{p.name}</p>
              <p style={{ fontSize: "12px", color: "#4a5568", marginTop: "2px" }}>
                „{p.query}"
                {p.min_price && ` · ab ${p.min_price}€`}
                {p.max_price && ` · bis ${p.max_price}€`}
                {p.custom_threshold && ` · Threshold ${p.custom_threshold}%`}
              </p>
            </div>

            <span
              style={{
                fontSize: "11px",
                fontWeight: 500,
                padding: "3px 10px",
                borderRadius: "20px",
                background: p.active ? "rgba(34,211,165,0.1)" : "rgba(74,85,104,0.15)",
                color: p.active ? "#22d3a5" : "#4a5568",
                flexShrink: 0,
              }}
            >
              {p.active ? "Aktiv" : "Inaktiv"}
            </span>

            {confirmDelete === p.id ? (
              <div style={{ display: "flex", gap: "6px", alignItems: "center", flexShrink: 0 }}>
                <span style={{ fontSize: "12px", color: "#ef4444" }}>Löschen?</span>
                <button
                  onClick={() => handleDelete(p.id!)}
                  style={{
                    fontSize: "11px",
                    fontWeight: 600,
                    color: "#f0f4ff",
                    background: "#ef4444",
                    border: "none",
                    padding: "4px 10px",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontFamily: "inherit",
                  }}
                >
                  Ja
                </button>
                <button
                  onClick={() => setConfirmDelete(null)}
                  style={{
                    fontSize: "11px",
                    fontWeight: 500,
                    color: "#8a97b0",
                    background: "#19212e",
                    border: "none",
                    padding: "4px 10px",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontFamily: "inherit",
                  }}
                >
                  Nein
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDelete(p.id!)}
                style={{
                  color: "#4a5568",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  display: "flex",
                  padding: "2px",
                  transition: "color 0.15s ease",
                  flexShrink: 0,
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#ef4444")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "#4a5568")}
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
        ))}

        {profiles.length === 0 && (
          <div style={{ textAlign: "center", padding: "48px 0" }}>
            <p style={{ fontSize: "32px", marginBottom: "12px" }}>🔍</p>
            <p style={{ fontSize: "13px", color: "#4a5568" }}>Noch keine Profile. Erstelle dein erstes Suchprofil.</p>
          </div>
        )}
      </div>
    </div>
  );
}
