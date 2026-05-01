import { useEffect, useState } from "react";
import { MessageSquare, Settings, Search, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import api, { type AIWorker } from "../api";
import { getGrantedSkills } from "../skills";

const TENANT_ID = "d9099572-afd0-45d9-b30c-03a289e79b15";

export default function Workers() {
  const [workers, setWorkers] = useState<AIWorker[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", role: "", persona: "" });
  const [creating, setCreating] = useState(false);
  const recommendedSkills = getGrantedSkills(form.role);

  useEffect(() => {
    api.get(`/workers/tenant/${TENANT_ID}`)
      .then(res => setWorkers(res.data))
      .finally(() => setLoading(false));
  }, []);

  const filtered = workers.filter(w =>
    w.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleCreate = async () => {
    if (!form.name || !form.role) return;
    setCreating(true);
    try {
      const res = await api.post("/workers/", {
        tenant_id: TENANT_ID,
        name: form.name,
        role: form.role,
        persona: form.persona,
      });
      setWorkers(prev => [...prev, res.data]);
      setShowCreate(false);
      setForm({ name: "", role: "", persona: "" });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="flex-1 p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Workers</h1>
          <p className="text-gray-500 text-sm mt-1">Manage and interact with your AI workforce</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition"
        >
          <Plus size={16} />
          Hire Worker
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-6 max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search workers by name..."
          className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
        />
      </div>

      {/* Workers Grid */}
      {loading ? (
        <p className="text-gray-400 text-sm">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(worker => (
            <WorkerCard key={worker.id} worker={worker} />
          ))}
          {filtered.length === 0 && (
            <p className="text-gray-400 text-sm col-span-3">No workers found.</p>
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-semibold mb-4">Hire a new worker</h2>
            <div className="space-y-3">
              <input
                placeholder="Name (e.g. Sofia)"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              <input
                placeholder="Role (e.g. Executive Assistant)"
                value={form.role}
                onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              <textarea
                placeholder="Persona / instructions (optional)"
                value={form.persona}
                onChange={e => setForm(f => ({ ...f, persona: e.target.value }))}
                rows={3}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"
              />
            </div>
            <div className="mt-4 rounded-lg border border-emerald-100 bg-emerald-50/60 p-3">
              <p className="text-xs font-semibold text-emerald-800 mb-2">
                Recommended skills for this role
              </p>
              {recommendedSkills.length === 0 ? (
                <p className="text-xs text-emerald-700">
                  Add a role title to see which permissions this worker will likely need.
                </p>
              ) : (
                <div className="space-y-2">
                  {recommendedSkills.map((skill) => (
                    <div key={skill.key} className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-medium text-emerald-900">{skill.label}</p>
                        <p className="text-[11px] text-emerald-700">{skill.description}</p>
                      </div>
                      <span className="text-[10px] px-2 py-1 rounded-full bg-white border border-emerald-200 text-emerald-700">
                        Needed
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <p className="text-[11px] text-emerald-700 mt-2">
                Permissions can be reviewed and activated when opening chat.
              </p>
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => setShowCreate(false)}
                className="flex-1 border border-gray-200 rounded-lg py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={creating}
                className="flex-1 bg-green-600 text-white rounded-lg py-2 text-sm hover:bg-green-700 disabled:opacity-50"
              >
                {creating ? "Hiring..." : "Hire"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function WorkerCard({ worker }: { worker: AIWorker }) {
  const initials = worker.name.split(" ").map(n => n[0]).join("").toUpperCase();
  const colors = [
    "bg-violet-100 text-violet-700",
    "bg-blue-100 text-blue-700",
    "bg-rose-100 text-rose-700",
    "bg-amber-100 text-amber-700",
  ];
  const color = colors[worker.name.charCodeAt(0) % colors.length];

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden hover:shadow-md transition">
      <div className="flex">
        <div className={`w-32 flex items-center justify-center text-3xl font-bold ${color}`}>
          {initials}
        </div>
        <div className="p-4 flex-1">
          <h3 className="font-semibold text-gray-900">{worker.name}</h3>
          <p className="text-sm text-gray-500 mb-3">{worker.role}</p>
          <div className="flex items-center gap-2">
            <Link
              to={`/chat/${worker.id}`}
              className="flex items-center gap-1 text-xs border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition"
            >
              <MessageSquare size={13} />
              Chat
            </Link>
            <button className="flex items-center gap-1 text-xs border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition">
              <Settings size={13} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}