import sublime
import sublime_plugin
from datetime import date

class GenerateHeaderCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command("insert_snippet", {"name": "Packages/UVM/Snippets/header.sublime-snippet"})
        self.view.run_command("insert", {"characters" : str(date.today())})
        self.view.run_command("next_field")

class GenerateHeaderEventListener(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):

        return [
            sublime.CompletionItem.command_completion(
                "header",
                "generate_header",
                {

                },
                "Header",
                sublime.KIND_SNIPPET,
                details="Empty header for new file"
            )
        ]
