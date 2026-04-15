"""
Keep-like Note App - Comprehensive Implementation
Continues prior spec: data models, engine, AI integration, UI layer,
plus numbering, version history, cross-reference, pattern recognition,
and persistent memory.
"""

from __future__ import annotations
import json
import re
import uuid
import copy
import hashlib
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Constants & Data Models
# ---------------------------------------------------------------------------

NOTE_COLORS = ["White", "Red", "Orange", "Yellow", "Green", "Teal",
               "Blue", "Dark Blue", "Purple", "Pink", "Brown", "Gray"]
NOTE_TYPES = ["TEXT", "CHECKLIST", "VOICE", "IMAGE", "DRAWING"]
BACKGROUND_THEMES = [None, "Travel", "Food", "Video", "Music",
                     "Celebration", "Recipe", "Places", "Notes"]
TRASH_RETENTION_DAYS = 7


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


class Note:
    def __init__(self, id=None, owner_id=None, type="TEXT"):
        self.id = id or str(uuid.uuid4())
        self.owner_id = owner_id
        self.type = type
        self.title = ""
        self.content = ""
        self.check_items = []          # [{text, checked, indent}]
        self.media_urls = []
        self.labels = []               # supports "Parent/Child"
        self.color = "White"
        self.background_theme = None
        self.is_pinned = False
        self.is_archived = False
        self.is_trashed = False
        self.trashed_at = None
        self.is_locked = False
        self.numbering_enabled = False  # (1) numbering option per note
        self.reminder = {"timestamp": None, "location": None, "recurrence": None}
        self.collaborators = []
        self.created_at = _now()
        self.last_edited = self.created_at
        self.versions = []             # (2) time-stamped version history
        self.cross_refs = set()        # (3) note IDs this note references
        self.patterns = {}             # (4) pattern recognition cache
        self.formatting = {"bold": [], "italic": [], "underline": [],
                           "strikethrough": [], "headings": []}

    # ------- serialization -------
    def to_dict(self):
        d = self.__dict__.copy()
        d["cross_refs"] = list(self.cross_refs)
        return d

    @classmethod
    def from_dict(cls, d):
        n = cls(id=d["id"], owner_id=d.get("owner_id"), type=d.get("type", "TEXT"))
        for k, v in d.items():
            setattr(n, k, v)
        n.cross_refs = set(d.get("cross_refs", []))
        return n

    # ------- version history (2) -------
    def snapshot(self, reason="edit"):
        self.versions.append({
            "timestamp": _now(),
            "reason": reason,
            "title": self.title,
            "content": self.content,
            "check_items": copy.deepcopy(self.check_items),
            "labels": list(self.labels),
            "color": self.color,
        })

    def restore_version(self, index):
        if 0 <= index < len(self.versions):
            v = self.versions[index]
            self.snapshot("pre-restore")
            self.title = v["title"]
            self.content = v["content"]
            self.check_items = copy.deepcopy(v["check_items"])
            self.labels = list(v["labels"])
            self.color = v["color"]
            self.last_edited = _now()
            return True
        return False

    # ------- numbering (1) -------
    def render_numbered(self) -> str:
        if not self.numbering_enabled:
            return self.content
        lines = self.content.splitlines()
        return "\n".join(f"{i+1}. {ln}" if ln.strip() else ln
                         for i, ln in enumerate(lines))


# ---------------------------------------------------------------------------
# 2. Persistent Memory (5) - consistent across sessions
# ---------------------------------------------------------------------------

class ConsistentMemory:
    """Persists engine state + a recall log so sessions continue seamlessly."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = {"notes": {}, "session": {}, "recall": []}
        self.load()

    def load(self):
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def remember(self, key, value):
        self.data["session"][key] = value
        self.data["recall"].append({"t": _now(), "key": key})
        self.save()

    def last_context(self):
        return self.data["session"].get("last_context")


# ---------------------------------------------------------------------------
# 3. Pattern Recognition (4) + Cross-Reference (3)
# ---------------------------------------------------------------------------

class PatternEngine:
    URL_RE = re.compile(r"https?://\S+")
    EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    PHONE_RE = re.compile(r"\+?\d[\d\s\-()]{7,}\d")
    DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b")
    HASHTAG_RE = re.compile(r"#\w+")
    MENTION_RE = re.compile(r"@\w+")
    TODO_RE = re.compile(r"\b(todo|fixme|remember to|don'?t forget)\b", re.I)
    XREF_RE = re.compile(r"\[\[([0-9a-f\-]{8,})\]\]")  # [[note-id]]

    @classmethod
    def analyze(cls, text: str) -> dict:
        return {
            "urls": cls.URL_RE.findall(text),
            "emails": cls.EMAIL_RE.findall(text),
            "phones": cls.PHONE_RE.findall(text),
            "dates": cls.DATE_RE.findall(text),
            "hashtags": cls.HASHTAG_RE.findall(text),
            "mentions": cls.MENTION_RE.findall(text),
            "has_todo": bool(cls.TODO_RE.search(text)),
            "word_count": len(text.split()),
            "sentiment_hint": cls._sentiment(text),
        }

    @staticmethod
    def _sentiment(text: str) -> str:
        pos = sum(w in text.lower() for w in ["good", "great", "love", "happy", "nice"])
        neg = sum(w in text.lower() for w in ["bad", "sad", "hate", "angry", "worst"])
        return "positive" if pos > neg else "negative" if neg > pos else "neutral"

    @classmethod
    def extract_refs(cls, text: str) -> set:
        return set(cls.XREF_RE.findall(text))


# ---------------------------------------------------------------------------
# 4. Core Engine
# ---------------------------------------------------------------------------

class KeepEngine:
    def __init__(self, user_id, memory_path="keep_memory.json"):
        self.user_id = user_id
        self.memory = ConsistentMemory(Path(memory_path))
        self.notes: dict[str, Note] = {
            nid: Note.from_dict(d) for nid, d in self.memory.data["notes"].items()
        }
        self.undo_stack = []
        self.redo_stack = []

    # --- persistence bridge ---
    def _persist(self):
        self.memory.data["notes"] = {nid: n.to_dict() for nid, n in self.notes.items()}
        self.memory.data["session"]["last_context"] = {
            "time": _now(), "count": len(self.notes),
        }
        self.memory.save()

    def resume(self):
        ctx = self.memory.last_context()
        return f"Resumed with {len(self.notes)} notes (last: {ctx})" if ctx else "Fresh session"

    # --- Creation ---
    def create_note(self, type="TEXT", title="", content="") -> Note:
        n = Note(owner_id=self.user_id, type=type)
        n.title, n.content = title, content
        n.snapshot("create")
        self._reindex(n)
        self.notes[n.id] = n
        self.undo_stack.append(("create", n.id))
        self._persist()
        return n

    def edit_note(self, note_id, **fields):
        n = self.notes.get(note_id)
        if not n:
            return None
        n.snapshot("edit")
        for k, v in fields.items():
            if hasattr(n, k):
                setattr(n, k, v)
        n.last_edited = _now()
        self._reindex(n)
        self._persist()
        return n

    def _reindex(self, n: Note):
        text = f"{n.title}\n{n.content}\n" + "\n".join(i.get("text", "") for i in n.check_items)
        n.patterns = PatternEngine.analyze(text)
        n.cross_refs = PatternEngine.extract_refs(text)

    # --- Media ---
    def add_voice_memo(self, note_id, audio_blob):
        n = self.notes[note_id]
        url = f"cloud://voice/{hashlib.md5(audio_blob).hexdigest()}"
        n.media_urls.append(url)
        n.type = "VOICE"
        n.content += f"\n[transcript of {url}]"
        self._reindex(n); self._persist()
        return url

    def grab_image_text(self, note_id, image_id):
        # OCR stub
        ocr_text = f"[OCR:{image_id}]"
        n = self.notes[note_id]
        n.content += f"\n{ocr_text}"
        self._reindex(n); self._persist()
        return ocr_text

    # --- Organization ---
    def set_reminder(self, note_id, time, location=None, recurrence=None):
        n = self.notes[note_id]
        n.reminder = {"timestamp": time, "location": location, "recurrence": recurrence}
        self._persist()

    def snooze_reminder(self, note_id, delta: timedelta):
        n = self.notes[note_id]
        if n.reminder["timestamp"]:
            t = datetime.fromisoformat(n.reminder["timestamp"].rstrip("Z"))
            n.reminder["timestamp"] = (t + delta).isoformat() + "Z"
            self._persist()

    def update_labels(self, note_id, label_list):
        self.notes[note_id].labels = label_list
        self._persist()

    def batch_action(self, note_ids, action, **kwargs):
        for nid in note_ids:
            n = self.notes.get(nid)
            if not n: continue
            if action == "archive":   n.is_archived = True
            elif action == "unarchive": n.is_archived = False
            elif action == "pin":     n.is_pinned = True
            elif action == "unpin":   n.is_pinned = False
            elif action == "trash":
                n.is_trashed = True; n.trashed_at = _now()
            elif action == "color":   n.color = kwargs.get("color", "White")
            elif action == "label":   n.labels.extend(kwargs.get("labels", []))
        self._persist()

    def empty_trash(self):
        cutoff = datetime.utcnow() - timedelta(days=TRASH_RETENTION_DAYS)
        for nid in list(self.notes):
            n = self.notes[nid]
            if n.is_trashed and n.trashed_at:
                t = datetime.fromisoformat(n.trashed_at.rstrip("Z"))
                if t < cutoff:
                    del self.notes[nid]
        self._persist()

    # --- Search ---
    def search(self, query="", filters=None):
        filters = filters or {}
        q = query.lower()
        hits = []
        for n in self.notes.values():
            if n.is_trashed and not filters.get("include_trash"): continue
            hay = f"{n.title} {n.content} {' '.join(n.labels)}".lower()
            if q and q not in hay and not self._smart_match(q, n): continue
            if "color" in filters and n.color != filters["color"]: continue
            if "type" in filters and n.type != filters["type"]: continue
            if "label" in filters and filters["label"] not in n.labels: continue
            if filters.get("has_reminder") and not n.reminder["timestamp"]: continue
            hits.append(n)
        return sorted(hits, key=lambda x: (not x.is_pinned, x.last_edited), reverse=False)

    def _smart_match(self, q, n: Note) -> bool:
        # "AI object detection" stub: checks patterns/labels
        return any(q in v.lower() for v in [*n.labels, *n.patterns.get("hashtags", [])])

    # --- Cross-reference graph (3) ---
    def backlinks(self, note_id):
        return [n for n in self.notes.values() if note_id in n.cross_refs]

    def reference_graph(self):
        g = defaultdict(list)
        for n in self.notes.values():
            for r in n.cross_refs:
                g[n.id].append(r)
        return dict(g)

    # --- Undo / Redo ---
    def undo(self):
        if not self.undo_stack: return
        action, nid = self.undo_stack.pop()
        if action == "create" and nid in self.notes:
            self.redo_stack.append(("recreate", self.notes[nid].to_dict()))
            del self.notes[nid]
        self._persist()

    def redo(self):
        if not self.redo_stack: return
        action, payload = self.redo_stack.pop()
        if action == "recreate":
            n = Note.from_dict(payload)
            self.notes[n.id] = n
        self._persist()


# ---------------------------------------------------------------------------
# 5. AI / Gemini Integration (stubs)
# ---------------------------------------------------------------------------

class GeminiIntegrator:
    def __init__(self, engine: KeepEngine):
        self.engine = engine

    def summarize_note(self, note_id):
        n = self.engine.notes[note_id]
        sents = re.split(r"(?<=[.!?])\s+", n.content.strip())
        top = sents[:3]
        return [f"• {s}" for s in top if s]

    def suggest_action_items(self, note_id):
        n = self.engine.notes[note_id]
        items = []
        for line in n.content.splitlines():
            if PatternEngine.TODO_RE.search(line) or line.strip().startswith("-"):
                items.append({"text": line.strip("- ").strip(), "checked": False})
        return items

    def translate_note(self, note_id, target_lang):
        n = self.engine.notes[note_id]
        return f"[{target_lang}] {n.content}"

    def suggest_labels(self, note_id):
        n = self.engine.notes[note_id]
        tags = n.patterns.get("hashtags", [])
        return [t.lstrip("#") for t in tags][:5]

    def help_me_create(self, topic):
        templates = {
            "trip": ["Passport", "Tickets", "Hotel", "Itinerary"],
            "grocery": ["Milk", "Bread", "Eggs", "Vegetables"],
        }
        return templates.get(topic.lower(), ["Item 1", "Item 2", "Item 3"])


# ---------------------------------------------------------------------------
# 6. Workspace Sync (stubs)
# ---------------------------------------------------------------------------

class WorkspaceSync:
    def __init__(self, engine): self.engine = engine
    def export_to_docs(self, note_id):
        n = self.engine.notes[note_id]
        return {"doc_id": str(uuid.uuid4()), "title": n.title or "Untitled",
                "body": n.render_numbered()}
    def send_to(self, note_id, target):
        return f"sent:{target}:{note_id}"
    def sync_sidebar_state(self):
        return {"gmail": True, "calendar": True, "docs": True}


# ---------------------------------------------------------------------------
# 7. UI Layer (mock)
# ---------------------------------------------------------------------------

class KeepInterface:
    def __init__(self, engine):
        self.engine = engine
        self.view_mode = "GRID"
        self.order = []

    def toggle_view_mode(self):
        self.view_mode = "LIST" if self.view_mode == "GRID" else "GRID"
        return self.view_mode

    def handle_drag_reorder(self, note_id, new_position):
        if note_id in self.order: self.order.remove(note_id)
        self.order.insert(new_position, note_id)

    def open_drawing_canvas(self, tool="pen", background="plain"):
        return {"tool": tool, "background": background,
                "tools": ["pen", "marker", "highlighter", "eraser", "lasso"],
                "backgrounds": ["plain", "square", "dot", "ruled"]}

    def apply_biometric_lock(self, note_id):
        self.engine.notes[note_id].is_locked = True
        return "locked"


# ---------------------------------------------------------------------------
# 8. Shortcut dispatcher
# ---------------------------------------------------------------------------

SHORTCUTS_JS = """
const shortcuts = {
  'c': () => createNewNote(),
  'l': () => createNewList(),
  '/': () => focusSearch(),
  'j': () => nav('next'), 'k': () => nav('prev'),
  'n': () => nav('next'), 'p': () => nav('prev'),
  'Enter': () => editSelected(), 'Escape': () => closeNote(),
  'x': () => selectNote(),
  'e': () => archiveSelected(),
  '#': () => deleteSelected(),
  'f': () => togglePin(),
  'ctrl+g': () => toggleView(),
  'ctrl+z': () => undoAction(), 'ctrl+y': () => redoAction(),
  'ctrl+a': () => selectAllText(),
  'ctrl+shift+c': () => toggleCheckboxes(),
  'shift+f': () => searchInNote(),
  'o': () => openMore(),
  'shift+?': () => showShortcutMap(),
};
"""


# ---------------------------------------------------------------------------
# 9. Demo
# ---------------------------------------------------------------------------

def demo():
    eng = KeepEngine(user_id="user-1")
    print(eng.resume())
    a = eng.create_note("TEXT", "Trip plan", "Book tickets\nPack passport\nTODO confirm hotel")
    b = eng.create_note("CHECKLIST", "Groceries", f"See [[{a.id}]] for context")
    eng.edit_note(a.id, numbering_enabled=True, labels=["Travel/2026"])
    gi = GeminiIntegrator(eng)
    print("summary:", gi.summarize_note(a.id))
    print("actions:", gi.suggest_action_items(a.id))
    print("numbered:\n", eng.notes[a.id].render_numbered())
    print("backlinks to a:", [n.title for n in eng.backlinks(a.id)])
    print("patterns:", eng.notes[a.id].patterns)
    print("search 'passport':", [n.title for n in eng.search("passport")])
    print("versions:", len(eng.notes[a.id].versions))


if __name__ == "__main__":
    demo()
