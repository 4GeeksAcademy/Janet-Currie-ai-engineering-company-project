import { placeholderCandidates } from "@/lib/mock-data";
import type {
  CandidateFilters,
  CandidateFormValues,
  CandidateNote,
  CandidateRecord,
  NoteCreate,
  RecordPatch,
} from "@/types/tracker";

const STORAGE_KEY = "healthcore-talent-pipeline";
const LATENCY_MS = 220;

export const trackerApiBaseUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "https://playground.4geeks.com/tracker/api/v1";

function wait(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function synchronizeCounts(candidate: CandidateRecord): CandidateRecord {
  return {
    ...candidate,
    notes_count: candidate.notes.length,
  };
}

function nextId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function readAllCandidates(): CandidateRecord[] {
  const seeded = placeholderCandidates.map(synchronizeCounts);

  if (typeof window === "undefined") {
    return clone(seeded);
  }

  const stored = window.localStorage.getItem(STORAGE_KEY);

  if (!stored) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(seeded));
    return clone(seeded);
  }

  try {
    const parsed = JSON.parse(stored) as CandidateRecord[];
    return clone(parsed.map(synchronizeCounts));
  } catch {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(seeded));
    return clone(seeded);
  }
}

function writeAllCandidates(candidates: CandidateRecord[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(candidates.map(synchronizeCounts)),
  );
}

function sortCandidates(candidates: CandidateRecord[]) {
  return [...candidates].sort((left, right) => {
    return (
      new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime()
    );
  });
}

function applyCandidateFilters(
  candidates: CandidateRecord[],
  filters: CandidateFilters = {},
) {
  const search = filters.search?.trim().toLowerCase();

  return candidates.filter((candidate) => {
    if (filters.status && candidate.status !== filters.status) {
      return false;
    }

    if (filters.stage && candidate.stage !== filters.stage) {
      return false;
    }

    if (filters.location && candidate.location_requested !== filters.location) {
      return false;
    }

    if (!search) {
      return true;
    }

    return [candidate.full_name, candidate.email].some((value) =>
      value.toLowerCase().includes(search),
    );
  });
}

function assertCandidate(
  candidates: CandidateRecord[],
  candidateId: string,
): CandidateRecord {
  const candidate = candidates.find((item) => item.id === candidateId);

  if (!candidate) {
    throw new Error("Candidate record could not be found.");
  }

  return candidate;
}

export async function listCandidates(filters: CandidateFilters = {}) {
  await wait(LATENCY_MS);

  return applyCandidateFilters(sortCandidates(readAllCandidates()), filters);
}

export async function getCandidate(candidateId: string) {
  await wait(LATENCY_MS);

  return synchronizeCounts(assertCandidate(readAllCandidates(), candidateId));
}

export async function createCandidate(values: CandidateFormValues) {
  await wait(LATENCY_MS);

  const candidates = readAllCandidates();
  const now = new Date().toISOString();

  const created: CandidateRecord = {
    id: nextId("cand"),
    full_name: values.full_name,
    email: values.email,
    phone: values.phone,
    position: values.position,
    location_requested: values.location_requested,
    linkedin_url: values.linkedin_url ?? null,
    cv_url: values.cv_url ?? null,
    status: "received",
    stage: "pending",
    experience_years: values.experience_years,
    notes_count: 0,
    applied_at: now,
    updated_at: now,
    notes: [],
  };

  writeAllCandidates([created, ...candidates]);

  return created;
}

export async function updateCandidate(
  candidateId: string,
  values: CandidateFormValues,
) {
  await wait(LATENCY_MS);

  const candidates = readAllCandidates();
  const candidate = assertCandidate(candidates, candidateId);
  const updated: CandidateRecord = {
    ...candidate,
    full_name: values.full_name,
    email: values.email,
    phone: values.phone,
    position: values.position,
    location_requested: values.location_requested,
    linkedin_url: values.linkedin_url ?? null,
    cv_url: values.cv_url ?? null,
    experience_years: values.experience_years,
    updated_at: new Date().toISOString(),
  };

  writeAllCandidates(
    candidates.map((item) => (item.id === candidateId ? updated : item)),
  );

  return updated;
}

export async function patchCandidate(
  candidateId: string,
  patch: RecordPatch,
) {
  await wait(LATENCY_MS);

  const candidates = readAllCandidates();
  const candidate = assertCandidate(candidates, candidateId);
  const updated: CandidateRecord = {
    ...candidate,
    status: patch.status ?? candidate.status,
    stage: patch.stage ?? candidate.stage,
    updated_at: new Date().toISOString(),
  };

  writeAllCandidates(
    candidates.map((item) => (item.id === candidateId ? updated : item)),
  );

  return updated;
}

export async function addCandidateNote(
  candidateId: string,
  note: NoteCreate,
) {
  await wait(LATENCY_MS);

  const candidates = readAllCandidates();
  const candidate = assertCandidate(candidates, candidateId);
  const nextNote: CandidateNote = {
    id: nextId("note"),
    author: "HealthCore Talent Ops",
    content: note.content,
    created_at: new Date().toISOString(),
  };

  const updated: CandidateRecord = {
    ...candidate,
    notes: [nextNote, ...candidate.notes],
    updated_at: new Date().toISOString(),
  };

  writeAllCandidates(
    candidates.map((item) => (item.id === candidateId ? updated : item)),
  );

  return synchronizeCounts(updated);
}

export async function deleteCandidateNote(
  candidateId: string,
  noteId: string,
) {
  await wait(LATENCY_MS);

  const candidates = readAllCandidates();
  const candidate = assertCandidate(candidates, candidateId);
  const updated: CandidateRecord = {
    ...candidate,
    notes: candidate.notes.filter((note) => note.id !== noteId),
    updated_at: new Date().toISOString(),
  };

  writeAllCandidates(
    candidates.map((item) => (item.id === candidateId ? updated : item)),
  );

  return synchronizeCounts(updated);
}