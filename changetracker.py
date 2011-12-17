import difflib
import functools
import os
import sublime
import sublime_plugin
from sublime import Region
from threading import Thread


class HighlightChangesCore:
    # highlight modes
    MODE_DOTS = "dots"
    MODE_TEXT = "text"

    def __init__(self):
        self.settings = sublime.load_settings(__name__ + '.sublime-settings')
        self.regions = []
        self._scope = "comment"
        self._current_region = 0
        self.diff_thread = None

    def highlight_as_you_type(self):
        return self.settings.get("highlight_as_you_type", True)

    def highlight_delay(self):
        return self.settings.get("highlight_delay", 2000)  # default delay is 2000ms

    def highlight_mode(self):
        return self.settings.get("highlight_mode", HighlightChangesCore.MODE_DOTS)  # default mode is "dots"

    def goto_next_diff(self, view):
        if self._current_region >= len(self.regions):
            self._current_region = 0
        if len(self.regions) > 0:
            view.show(self.regions[self._current_region])
        self._current_region += 1

    def get_diff(self, s1, s2):
        s = difflib.SequenceMatcher(None, s1, s2)
        unchanged = [(m[1], m[1] + m[2]) for m in s.get_matching_blocks()]
        diffs = []
        prev = unchanged[0]
        for u in unchanged[1:]:
                diffs.append((prev[1], u[0]))
                prev = u
        return diffs

    def highlight_sync(self, view, currentText, filename, mode):
        try:
            with open(filename, "rU") as f:
                originalText = f.read().decode('utf8')
            diffs = self.get_diff(originalText, currentText)
            if mode == HighlightChangesCore.MODE_TEXT:
                self.regions = [Region(d[0], d[1]) for d in diffs if d[0] != d[1]]
            if mode == HighlightChangesCore.MODE_DOTS:
                self.regions = [Region(d[1], d[1]) for d in diffs if d[0] != d[1]]
            # execute in gui thread
            sublime.set_timeout(functools.partial(view.add_regions, "changes", self.regions, self._scope, "dot"), 1)
        except:
            pass

    def is_enabled(self, view):
        if (view.file_name() and os.path.exists(view.file_name())):
            fs = os.path.getsize(view.file_name()) / 1024
            max_size = self.settings.get("max_allowed_file_size", 256)
            return fs < max_size
        else:
            return False

    def highlight(self, view):
        currentText = view.substr(Region(0, view.size()))
        filename = view.file_name()
        mode = self.highlight_mode()
        if self.is_enabled(view):
            self.diff_thread = Thread(target=self.highlight_sync, args=(view, currentText, filename, mode))
            if self.diff_thread.is_alive():
                pass
                #self.diff_thread._Thread__stop()
                #self.diff_thread.start()
            else:
                self.diff_thread.start()

    def clear(self, view):
        if view:
            view.add_regions("changes", [], "changes", "dot", sublime.DRAW_OUTLINED)


class HighlightchangesCommand(sublime_plugin.TextCommand):
    def __init__(self, edit):
        self.highlightCore = HighlightChangesCore()
        sublime_plugin.TextCommand.__init__(self, edit)

    def run(self, edit):
        self.highlightCore.highlight(self.view)


class GotonextdiffCommand(HighlightchangesCommand):
    def run(self, edit):
        self.highlightCore.highlight(self.view)
        self.highlightCore.goto_next_diff(self.view)


class HighlightWhenTypingListener(sublime_plugin.EventListener):
    def __init__(self):
        self.timer = None
        self.pending = 0
        self.highlightCore = HighlightChangesCore()

    def handle_timeout(self, view):
        self.pending = self.pending - 1
        if self.pending == 0:
            self.on_idle(view)

    def on_idle(self, view):
        view.run_command("highlightchanges")

    def on_modified(self, view):
        if self.highlightCore.highlight_as_you_type():
            self.pending = self.pending + 1
            sublime.set_timeout(functools.partial(self.handle_timeout, view), self.highlightCore.highlight_delay())

    def on_post_save(self, view):
        self.highlightCore.clear(view)
