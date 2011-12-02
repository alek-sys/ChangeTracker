import difflib
import codecs
import functools
import sublime
import sublime_plugin

from sublime import Region
from threading import Timer

class HighlightChangesCore:
    def __init__(self):
        self.settings = sublime.load_settings(__name__ + '.sublime-settings')
        self.regions = []
        self._scope = "markup.changed"

    def highlight_as_you_type(self):
        if self.settings.get("highlight_as_you_type"):
            return self.settings.get("highlight_as_you_type")
        else:
            return true

    def highlight_delay(self):
        if self.settings.get("highlight_delay"):
            return self.settings.get("highlight_delay")
        else:
            return 2000 # default delay is 2000ms

    def get_diff(self, s1, s2):   
        s = difflib.SequenceMatcher(None, s1, s2)        
        unchanged = [(m[1], m[1] + m[2]) for m in s.get_matching_blocks()] # if not (m[0]==len(s1) and m[1]==len(s2) and m[2]==0)]
        diffs = []
        prev = unchanged[0]
        for u in unchanged[1:]:
                diffs.append((prev[1], u[0]))
                prev = u
        return diffs

    def highlight(self, view):
        currentText = view.substr(Region(0, view.size()))        
        originalText = codecs.open(view.file_name(), "r", "utf-8").read()
        diffs = self.get_diff(originalText, currentText)
        self.regions = [Region(d[0], d[1]) for d in diffs if d[0] != d[1]]
        view.add_regions("changes", self.regions, self._scope, "dot")

    def clear(self, view):
        view.add_regions("changes", [], "changes", "dot")

class HighlightchangesCommand(sublime_plugin.TextCommand):
    def __init__(self, view):
        self.highlightCore = HighlightChangesCore()
        sublime_plugin.TextCommand.__init__(self, view)

    def run(self, edit): 
        self.highlightCore.highlight(self.view)

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