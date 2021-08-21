import sublime
import sublime_plugin
import os.path

list_of_uvm_components=['environment', 'reference_module', 'sequence']

class ProjectNameInputHandler(sublime_plugin.TextInputHandler):
    def __init__(self, last_project_name):
        self.last_project_name = last_project_name

    def initial_text(self):
        return self.last_project_name or ""

    def preview(self, text):
        if text:
            if text[0].isalnum() and all(x.isalpha() or x.isspace() for x in text) == False:
                return 'Invalid project name'
        return "Enter project name"

    def validate(self, text):
        return text[0].isalnum() and all(x.isalpha() or x.isspace() for x in text)

    def next_input(self, args):
        if 'component_name' not in args:
            return ComponentNameInputHandler()


class ComponentNameInputHandler(sublime_plugin.ListInputHandler):

    def list_items(self):
        return list_of_uvm_components
    def placeholder(self):
        return 'Choose uvm component name'

class CreateFileTamplateCommand(sublime_plugin.WindowCommand):
    last_project_name = None

    def run(self, project_name = "", component_name = ""):
        self.last_project_name = project_name

        view = self.window.new_file()
        view.retarget(project_name.replace(" ", "_").lower()+"_"+component_name+".sv")
        self.window.run_command('prompt_save_as')

        view.run_command('generate_header')
        view.run_command('insert', {"characters" : project_name})
        view.run_command("next_field")
        view.run_command("insert_snippet", {"name": "Packages/UVM/Snippets/file_guard.sublime-snippet"})
        view.run_command("insert_snippet", {"name" : "Packages/UVM/Snippets/"+component_name+".sublime-snippet"})

        view.run_command('save')

        if component_name == 'environment':
            self.create_full_env(os.path.split(view.file_name())[0])

    def input(self, args):
        if 'project_name' not in args:
            return ProjectNameInputHandler(self.last_project_name)
        elif 'component_name' not in args:
            return ComponentNameInputHandler()

    def create_full_env(self, folder_path):
        with open(os.path.join(folder_path, 'reference_module'+'.sv'), 'wt') as reference_module:
            reference_module.write("This is a reference module")

