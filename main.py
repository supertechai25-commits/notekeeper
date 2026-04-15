"""NoteKeeper - Kivy mobile UI wrapping KeepEngine."""
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.core.window import Window
from pathlib import Path
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keep_app import KeepEngine, GeminiIntegrator  # noqa

try:
    from android.storage import app_storage_path  # type: ignore
    MEMORY = Path(app_storage_path()) / "keep_memory.json"
except Exception:
    MEMORY = Path.home() / ".notekeeper" / "keep_memory.json"
MEMORY.parent.mkdir(parents=True, exist_ok=True)


class NoteCard(Button):
    def __init__(self, note, on_open, **kw):
        super().__init__(**kw)
        self.note = note
        self.text = f"[b]{note.title or '(untitled)'}[/b]\n{note.content[:80]}"
        self.markup = True
        self.size_hint_y = None
        self.height = 120
        self.halign = "left"
        self.valign = "top"
        self.text_size = (Window.width - 30, None)
        self.background_color = (0.95, 0.95, 0.85, 1) if note.is_pinned else (1, 1, 1, 1)
        self.color = (0, 0, 0, 1)
        self.on_release = lambda: on_open(note)


class NoteKeeperApp(App):
    title = "NoteKeeper"

    def build(self):
        self.engine = KeepEngine(user_id="local", memory_path=str(MEMORY))
        self.gi = GeminiIntegrator(self.engine)

        root = BoxLayout(orientation="vertical")
        bar = BoxLayout(size_hint_y=None, height=50, spacing=4, padding=4)
        self.search_in = TextInput(hint_text="Search…", multiline=False)
        self.search_in.bind(on_text_validate=lambda *_: self.refresh())
        bar.add_widget(self.search_in)
        bar.add_widget(Button(text="+Note", on_release=lambda *_: self.new_note("TEXT"), size_hint_x=0.25))
        bar.add_widget(Button(text="+List", on_release=lambda *_: self.new_note("CHECKLIST"), size_hint_x=0.25))
        root.add_widget(bar)

        sv = ScrollView()
        self.grid = GridLayout(cols=1, size_hint_y=None, spacing=6, padding=6)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        sv.add_widget(self.grid)
        root.add_widget(sv)

        self.refresh()
        return root

    def refresh(self):
        self.grid.clear_widgets()
        q = self.search_in.text
        notes = self.engine.search(q) if q else [n for n in self.engine.notes.values() if not n.is_trashed]
        notes.sort(key=lambda n: (not n.is_pinned, n.last_edited), reverse=False)
        for n in notes:
            self.grid.add_widget(NoteCard(n, self.open_note))
        if not notes:
            self.grid.add_widget(Label(text="No notes yet. Tap +Note.", size_hint_y=None, height=60, color=(0.4, 0.4, 0.4, 1)))

    def new_note(self, type_):
        n = self.engine.create_note(type_, title="New " + type_.lower(), content="")
        self.open_note(n)

    def open_note(self, n):
        box = BoxLayout(orientation="vertical", spacing=6, padding=6)
        title = TextInput(text=n.title, hint_text="Title", size_hint_y=None, height=48, multiline=False)
        content = TextInput(text=n.content, hint_text="Content")
        row = BoxLayout(size_hint_y=None, height=48, spacing=4)
        pin = Button(text="Unpin" if n.is_pinned else "Pin")
        trash = Button(text="Trash")
        summarize = Button(text="Summarize")
        save = Button(text="Save")
        row.add_widget(pin); row.add_widget(summarize); row.add_widget(trash); row.add_widget(save)
        info = Label(text=f"v{len(n.versions)}  edited {n.last_edited}",
                     size_hint_y=None, height=24, color=(0.5, 0.5, 0.5, 1))
        box.add_widget(title); box.add_widget(content); box.add_widget(info); box.add_widget(row)
        pop = Popup(title="Note", content=box, size_hint=(0.95, 0.95))

        def do_save(*_):
            self.engine.edit_note(n.id, title=title.text, content=content.text)
            pop.dismiss(); self.refresh()

        def do_pin(*_):
            self.engine.batch_action([n.id], "unpin" if n.is_pinned else "pin")
            pop.dismiss(); self.refresh()

        def do_trash(*_):
            self.engine.batch_action([n.id], "trash")
            pop.dismiss(); self.refresh()

        def do_sum(*_):
            self.engine.edit_note(n.id, title=title.text, content=content.text)
            lines = self.gi.summarize_note(n.id)
            content.text += "\n\n--- Summary ---\n" + "\n".join(lines)

        save.bind(on_release=do_save)
        pin.bind(on_release=do_pin)
        trash.bind(on_release=do_trash)
        summarize.bind(on_release=do_sum)
        pop.open()


if __name__ == "__main__":
    NoteKeeperApp().run()
