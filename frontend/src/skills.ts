export type SkillKey =
  | "gmail_read"
  | "gmail_send"
  | "calendar_read"
  | "calendar_write"
  | "web_research"
  | "notes_write";

export interface SkillDefinition {
  key: SkillKey;
  label: string;
  description: string;
}

export const SKILL_DEFINITIONS: SkillDefinition[] = [
  {
    key: "gmail_read",
    label: "Gmail read",
    description: "Read incoming email threads and inbox context.",
  },
  {
    key: "gmail_send",
    label: "Gmail send",
    description: "Draft and send emails on your behalf.",
  },
  {
    key: "calendar_read",
    label: "Calendar read",
    description: "Check events and availability.",
  },
  {
    key: "calendar_write",
    label: "Calendar write",
    description: "Create and update calendar events.",
  },
  {
    key: "web_research",
    label: "Web research",
    description: "Search the web for external information.",
  },
  {
    key: "notes_write",
    label: "Notes write",
    description: "Save action notes and summaries.",
  },
];

export function resolveSkillsForRole(role: string): Record<SkillKey, boolean> {
  const roleNormalized = role.toLowerCase();
  const skills: Record<SkillKey, boolean> = {
    gmail_read: false,
    gmail_send: false,
    calendar_read: false,
    calendar_write: false,
    web_research: true,
    notes_write: true,
  };

  if (
    ["assistant", "executive", "operations", "support"].some((term) =>
      roleNormalized.includes(term),
    )
  ) {
    skills.gmail_read = true;
    skills.gmail_send = true;
    skills.calendar_read = true;
    skills.calendar_write = true;
  } else if (
    ["sales", "account manager", "customer success"].some((term) =>
      roleNormalized.includes(term),
    )
  ) {
    skills.gmail_read = true;
    skills.gmail_send = true;
  } else if (
    ["research", "analyst"].some((term) => roleNormalized.includes(term))
  ) {
    skills.web_research = true;
    skills.notes_write = true;
  }

  return skills;
}

export function getGrantedSkills(role: string): SkillDefinition[] {
  const grants = resolveSkillsForRole(role);
  return SKILL_DEFINITIONS.filter((skill) => grants[skill.key]);
}
