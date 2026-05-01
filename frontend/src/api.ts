import axios from "axios";

const api = axios.create({
  baseURL: "https://spinnable-clone.onrender.com/api",
});

export default api;

export interface Tenant {
  id: string;
  name: string;
  business_context: string;
  created_at: string;
}

export interface AIWorker {
  id: string;
  tenant_id: string;
  name: string;
  role: string;
  persona: string;
  is_active: boolean;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  conversation_id: string;
}

export interface GoogleAuthorizeResponse {
  authorization_url: string;
}

export interface GoogleStatusResponse {
  connected: boolean;
  granted_permissions: string[];
  missing_permissions: string[];
  connected_email?: string | null;
}