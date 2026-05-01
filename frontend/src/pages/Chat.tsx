import { useState, useRef, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Send } from "lucide-react";
import api, {
  type AIWorker,
  type Message,
  type GoogleAuthorizeResponse,
  type GoogleStatusResponse,
} from "../api";
import { getGrantedSkills, type SkillKey } from "../skills";
import { getSessionUserId } from "../session";

const TENANT_ID = "d9099572-afd0-45d9-b30c-03a289e79b15";
const GOOGLE_SKILLS: SkillKey[] = ["gmail_read", "gmail_send", "calendar_read", "calendar_write"];

export default function Chat() {
  const { workerId } = useParams();
  const [worker, setWorker] = useState<AIWorker | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [connectedEmail, setConnectedEmail] = useState<string | null>(null);
  const [sessionSkills, setSessionSkills] = useState<Record<SkillKey, boolean>>({
    gmail_read: false,
    gmail_send: false,
    calendar_read: false,
    calendar_write: false,
    web_research: false,
    notes_write: false,
  });
  const bottomRef = useRef<HTMLDivElement>(null);
  const sessionUserId = getSessionUserId();

  useEffect(() => {
    if (workerId) {
      api.get(`/workers/${workerId}`).then(res => setWorker(res.data));
    }
  }, [workerId]);

  useEffect(() => {
    if (!worker) return;
    setSessionSkills({
      gmail_read: false,
      gmail_send: false,
      calendar_read: false,
      calendar_write: false,
      web_research: false,
      notes_write: false,
    });
    setConnectedEmail(null);
    // Reset requested permissions every time a different worker chat opens.
  }, [worker?.id]);

  useEffect(() => {
    const syncOAuthStatus = async () => {
      if (!worker) return;
      const requiredGoogle = getGrantedSkills(worker.role)
        .map((skill) => skill.key)
        .filter((skill): skill is SkillKey => GOOGLE_SKILLS.includes(skill));
      if (requiredGoogle.length === 0) return;

      try {
        const status = await api.get<GoogleStatusResponse>("/integrations/google/status", {
          params: {
            tenant_id: TENANT_ID,
            user_id: sessionUserId,
            permissions: requiredGoogle,
          },
          paramsSerializer: {
            indexes: null,
          },
        });
        setConnectedEmail(status.data.connected_email ?? null);
        setSessionSkills((prev) => {
          const next = { ...prev };
          for (const permission of requiredGoogle) {
            next[permission] = status.data.granted_permissions.includes(permission);
          }
          return next;
        });
      } catch {
        // Keep UX non-blocking if status endpoint/table is not ready yet.
      }
    };

    void syncOAuthStatus();
  }, [worker?.id, worker?.role, sessionUserId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading || !workerId) return;

    const userMsg: Message = { role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const payload: Record<string, string> = {
        worker_id: workerId,
        tenant_id: TENANT_ID,
        user_id: sessionUserId,
        message: input,
      };
      if (conversationId) payload.conversation_id = conversationId;

      const res = await api.post("/chat/", payload);
      setConversationId(res.data.conversation_id);
      setMessages(prev => [...prev, { role: "assistant", content: res.data.reply }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Something went wrong. Try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const initials = worker?.name.split(" ").map(n => n[0]).join("").toUpperCase() ?? "?";
  const requiredSkills = worker ? getGrantedSkills(worker.role) : [];
  const pendingSkills = requiredSkills.filter((skill) => !sessionSkills[skill.key]);

  const parseApiError = (error: unknown) =>
    typeof error === "object" &&
    error &&
    "response" in error &&
    typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail === "string"
      ? (error as { response: { data: { detail: string } } }).response.data.detail
      : "Could not start authorization flow.";

  const postAuthRedirect = `${window.location.origin}/chat/${workerId ?? ""}`;

  const activateAllRecommended = async () => {
    const googlePermissions = requiredSkills
      .map((skill) => skill.key)
      .filter((skill): skill is SkillKey => GOOGLE_SKILLS.includes(skill));

    if (googlePermissions.length > 0 && workerId) {
      setAuthError(null);
      try {
        const response = await api.post<GoogleAuthorizeResponse>("/integrations/google/authorize", {
          worker_id: workerId,
          tenant_id: TENANT_ID,
          user_id: sessionUserId,
          permissions: googlePermissions,
          post_auth_redirect: postAuthRedirect,
        });
        const popup = window.open(response.data.authorization_url, "_blank", "noopener,noreferrer");
        if (!popup) {
          setAuthError("Popup blocked. Please allow popups to continue Google authorization.");
        }
      } catch (error: unknown) {
        setAuthError(parseApiError(error));
      }
    }

    const next = { ...sessionSkills };
    for (const skill of requiredSkills) next[skill.key] = true;
    setSessionSkills(next);
  };

  const requestGoogleAuthorization = async (permission: SkillKey) => {
    if (!workerId) return;
    setAuthError(null);
    try {
      const response = await api.post<GoogleAuthorizeResponse>("/integrations/google/authorize", {
        worker_id: workerId,
        tenant_id: TENANT_ID,
        user_id: sessionUserId,
        permissions: [permission],
        post_auth_redirect: postAuthRedirect,
      });
      const popup = window.open(response.data.authorization_url, "_blank", "noopener,noreferrer");
      if (!popup) {
        setAuthError("Popup blocked. Please allow popups to continue Google authorization.");
      }
    } catch (error: unknown) {
      setAuthError(parseApiError(error));
    }
  };

  const toggleSkill = async (skill: SkillKey) => {
    if (!sessionSkills[skill] && GOOGLE_SKILLS.includes(skill)) {
      await requestGoogleAuthorization(skill);
    }
    setSessionSkills((prev) => ({ ...prev, [skill]: !prev[skill] }));
  };

  return (
    <div className="flex-1 flex flex-col h-screen">
      {/* Top bar */}
      <div className="border-b border-gray-100 bg-white px-6 py-4 flex items-center gap-3">
        <Link to="/" className="text-gray-400 hover:text-gray-600">
          <ArrowLeft size={18} />
        </Link>
        <div className="w-8 h-8 rounded-full bg-violet-100 text-violet-700 flex items-center justify-center text-xs font-bold">
          {initials}
        </div>
        <div>
          <p className="font-semibold text-sm text-gray-900">{worker?.name ?? "Loading..."}</p>
          <p className="text-xs text-gray-400">{worker?.role}</p>
        </div>
      </div>

      {requiredSkills.length > 0 && (
        <div className="border-b border-emerald-100 bg-emerald-50 px-6 py-3">
          <div className="flex items-center justify-between gap-4 mb-2">
            <div>
              <p className="text-sm font-semibold text-emerald-900">Activate skills for this chat</p>
              <p className="text-xs text-emerald-800">
                {pendingSkills.length === 0
                  ? "All recommended permissions are active for this session."
                  : `${pendingSkills.length} permission(s) still need activation.`}
              </p>
              {connectedEmail && (
                <p className="text-[11px] text-emerald-700 mt-1">
                  Connected Google account: {connectedEmail}
                </p>
              )}
            </div>
            {pendingSkills.length > 0 && (
              <button
                onClick={() => void activateAllRecommended()}
                className="text-xs px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700"
              >
                Activate all recommended
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {requiredSkills.map((skill) => (
              <button
                key={skill.key}
                onClick={() => void toggleSkill(skill.key)}
                className={`text-xs px-3 py-1.5 rounded-full border transition ${
                  sessionSkills[skill.key]
                    ? "bg-emerald-600 border-emerald-600 text-white"
                    : "bg-white border-emerald-200 text-emerald-800 hover:bg-emerald-100"
                }`}
                title={skill.description}
              >
                {sessionSkills[skill.key] ? "Active" : "Activate"} - {skill.label}
              </button>
            ))}
          </div>
          {authError && <p className="mt-2 text-xs text-red-600">{authError}</p>}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 text-sm mt-20">
            Start a conversation with {worker?.name ?? "your worker"}
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-lg px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
              msg.role === "user"
                ? "bg-green-600 text-white rounded-br-sm"
                : "bg-white border border-gray-100 text-gray-800 rounded-bl-sm shadow-sm"
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-100 shadow-sm px-4 py-2.5 rounded-2xl rounded-bl-sm">
              <div className="flex gap-1 items-center h-4">
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-100 bg-white px-6 py-4">
        <div className="flex gap-3 items-end">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder={`Message ${worker?.name ?? "your worker"}...`}
            rows={1}
            className="flex-1 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-green-600 text-white p-2.5 rounded-xl hover:bg-green-700 disabled:opacity-40 transition"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}