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

export default function SearchProfiles() {
  const [profiles, setProfiles] = useState<SearchProfile[]>([]);
  const [form, setForm] = useState<Omit<SearchProfile, "id">>(EMPTY);
  const [showForm, setShowForm] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const load = () =>
    api.profiles.list().then((res) => setProfiles(res.profiles));

  useEffect(() => { load(); }, []);

  const handleToggle = async (p: SearchProfile) => {
    await api.profiles.update(p.id!, { ...p, active: !p.active });
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
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Suchprofile</h2>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex items-center gap-2 text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg"
        >
          <Plus size={15} /> Neu
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6 flex flex-col gap-4"
        >
          <h3 className="text-sm font-semibold text-gray-300">Neues Profil</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-400">Name *</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="Nintendo Switch"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-400">Suchbegriff *</label>
              <input
                required
                value={form.query}
                onChange={(e) => setForm({ ...form, query: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="Nintendo Switch OLED"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-400">Min Preis (€)</label>
              <input
                type="number"
                value={form.min_price ?? ""}
                onChange={(e) =>
                  setForm({ ...form, min_price: e.target.value ? Number(e.target.value) : null })
                }
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="0"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-400">Max Preis (€)</label>
              <input
                type="number"
                value={form.max_price ?? ""}
                onChange={(e) =>
                  setForm({ ...form, max_price: e.target.value ? Number(e.target.value) : null })
                }
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="500"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-400">Threshold % (optional)</label>
              <input
                type="number"
                value={form.custom_threshold ?? ""}
                onChange={(e) =>
                  setForm({
                    ...form,
                    custom_threshold: e.target.value ? Number(e.target.value) : null,
                  })
                }
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="35"
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="text-sm text-gray-400 hover:text-white px-4 py-2 rounded-lg bg-gray-800"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              disabled={saving}
              className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
            >
              {saving ? "Speichern…" : "Speichern"}
            </button>
          </div>
        </form>
      )}

      <div className="flex flex-col gap-3">
        {profiles.map((p) => (
          <div
            key={p.id}
            className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4"
          >
            <button
              onClick={() => handleToggle(p)}
              className={p.active ? "text-green-400" : "text-gray-600"}
              title={p.active ? "Deaktivieren" : "Aktivieren"}
            >
              {p.active ? <ToggleRight size={24} /> : <ToggleLeft size={24} />}
            </button>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-white">{p.name}</p>
              <p className="text-xs text-gray-400">
                „{p.query}"
                {p.min_price && ` · ab ${p.min_price}€`}
                {p.max_price && ` · bis ${p.max_price}€`}
                {p.custom_threshold && ` · Threshold ${p.custom_threshold}%`}
              </p>
            </div>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                p.active ? "bg-green-900 text-green-400" : "bg-gray-800 text-gray-500"
              }`}
            >
              {p.active ? "Aktiv" : "Inaktiv"}
            </span>
            {confirmDelete === p.id ? (
              <div className="flex gap-2 items-center">
                <span className="text-xs text-red-400">Löschen?</span>
                <button
                  onClick={() => handleDelete(p.id!)}
                  className="text-xs bg-red-700 text-white px-2 py-1 rounded"
                >
                  Ja
                </button>
                <button
                  onClick={() => setConfirmDelete(null)}
                  className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded"
                >
                  Nein
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDelete(p.id!)}
                className="text-gray-600 hover:text-red-400 transition-colors"
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
        ))}
        {profiles.length === 0 && (
          <p className="text-center py-12 text-gray-500">Noch keine Profile.</p>
        )}
      </div>
    </div>
  );
}
