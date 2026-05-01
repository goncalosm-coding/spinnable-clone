const SESSION_USER_ID_KEY = "spinnable_session_user_id";

export function getSessionUserId(): string {
  const existing = window.localStorage.getItem(SESSION_USER_ID_KEY);
  if (existing) return existing;

  const generated = window.crypto.randomUUID();
  window.localStorage.setItem(SESSION_USER_ID_KEY, generated);
  return generated;
}
