import sublime
import sublime_plugin


def parse_command_line(view, file_content):
    """
    Fcuntion to parse a command line.
    The command line should look like the following: function_name(args); second_function(more_args)
    The ';' is used as a sperator between the functions
    Using the line the cursor is at, it will parse the command and return a list of function
    Args can be anything and even more functions
    :param view: the view to the buffer
    :param file_content: the content of the buffer
    :return: a list of function gain from the command line, any warnings and errors that rose during the fcuntion
    """

    warnings = []
    errors = []
    functions_list = []

    # Get the line of the cursor
    # FIXME: works with only 1 cursor
    cursors_line = view.rowcol(view.sel()[0].begin())[0]

    # Get the command line from the file, split it using the ';' character, and strip it
    command_line = file_content[cursors_line].replace(' ', '').split(';')

    # This algorithm is shit, feel free to change it :)
    # It is used to add '' to all the arguments of the function on the command line
    # So that if the command line is "function_name(first, second)" it will become "function_name('first','second')""
    # The problem is what if the argument themselves are functions?

    """ Loop on the entire list in reverse because the first command in the command line is the
    most important and should execute last
    The command is changed to a list because string is immutable in python
    The second loop iterate over every character in the command and track the number of function in the command
    The state goes up by 1 when entering a parentheses '(' and goes down by 1 when leaving a parentheses ')'
    Using this logic the first ( is replace with (' and the last ) is replace with ')
    Any , in the parentheses of the first function (when state = 1) will be replace with ','"""
    for command in command_line[::-1]:

        # Skip any empty commands
        if command == '':
            continue

        # Reset the state and the function
        # The state goes up by 1 when entering a parentheses '(' and goes down by 1 when leaving a parentheses ')'
        state = 0
        function = []

        # The command is changed to a list because string is immutable in python
        command = list(command)

        # The second loop iterate over every character in the command and track the number of function in the command
        # The first ( is replace with (' and the last ) is replace with ')
        # Any , in the parentheses of the first function (when state = 1) will be replace with ','"""
        for index in range(len(command)):
            if command[index] == ')':
                state -= 1
                if state == 0:
                    function.append('\'')

            if command[index] == ',' and state == 1:
                function.append('\'')

            function.append(command[index])

            if command[index] == ',' and state == 1:
                function.append('\'')

            if command[index] == '(':
                state += 1
                if state == 1:
                    function.append('\'')

        if state > 0:
            errors.append("Can't find closing parentheses")
        elif state < 0:
            errors.append("Can't find opening parentheses")
        else:
            # Change the list back to string and add it to the functions list
            functions_list.append(''.join(function))

    return functions_list, warnings, errors


class DeclarationItem:
    """
    A class used to represent instructions used to declare item

    ...

    Attributes
    ----------
    function_name : str
        the name of the function that the text will be inserted to
    text : str
        the text that will be inserted to declare the item
        the text will be changed before being inserted to the file
        for example: 'component_type' might be replace with the actual component_type of the item
            same goes for the component_name
    uvm_type : str (component/agent/reference model/scoreboard/coverage)
        the uvm_type of the item, determined the content of the comment that will be added to the declaration
    comment : str
        the comment that will be added to the declaration

    Methods
    -------
    init(function_name, text, uvm_type="component", comment_type="line")
        Initialize the object
    """

    def __init__(self, function_name, text, uvm_type="component", comment_type="line"):
        """
        Initialize the object and generate a comment for the declaration
        :param function_name: the name of the function that the text will be inserted to
        :param text: the text that will be inserted to declare the item
        :param uvm_type: the uvm_type of the item, determined the content of the comment that will be added to the declaration
        :param comment_type: the type of the comment, can be 'line' or 'block'
        """
        self.function_name = function_name
        self.text = text
        self.uvm_type = uvm_type.title()
        if comment_type == "line":
            self.comment = '// ' + self.uvm_type
        elif comment_type == "block":
            self.comment = """/*------------------------------------------------------------------------------
--  """ + self.uvm_type + """
------------------------------------------------------------------------------*/"""


class DeclareComponentCommand(sublime_plugin.TextCommand):
    """
    A class used to represent an Animal

    ...

    Attributes
    ----------
    says_str : str
        a formatted string to print out what the animal says
    name : str
        the name of the animal
    sound : str
        the sound that the animal makes
    num_legs : int
        the number of legs the animal has (default 4)

    Methods
    -------
    says(sound=None)
        Prints the animals name and what sound it makes
    """
    warnings = {}
    errors = {}
    modified_text = []
    file_content = ""
    cursors_line = 0
    modified_command_line = None
    basic_completions = []

    def run(self, edit):
        """

        :param edit:
        :return:
        """
        self.warnings = []
        self.errors = []
        self.modified_text = []
        self.file_content = self.view.substr(sublime.Region(0, self.view.size())).split('\n')
        self.cursors_line = self.view.rowcol(self.view.sel()[0].begin())[0]
        self.modified_command_line = DeclarationItem(None, 'component_type component_name = null;')
        self.basic_completions = [
            DeclarationItem('new', 'this.component_name = null;'),
            DeclarationItem('build_phase',
                            'this.component_name = component_type::type_id::create(\"component_name\", this);',
                            comment_type="block")

        ]

        list_of_functions, self.warnings, self.errors = parse_command_line(self.view, self.file_content)

        if self.check_errors(edit):
            return

        for function in list_of_functions:
            exec('self.' + function)

        self.view.replace(edit, sublime.Region(0, self.view.size()), '\n'.join(self.modified_text))
        self.view.run_command("goto_line", {"line": self.cursors_line + 1})

    def check_errors(self, edit):
        """

        :return:
        """
        if len(self.errors):
            self.modified_text = self.file_content
            self.view.run_command('goto_line', {'line': self.cursors_line + 1})
            self.view.run_command('move_to', {'to': 'eol'})
            a = self.view.sel()[0].begin()
            self.view.run_command('insert', {"characters" : '// Error: ' + ''.join(self.errors)})
            b = self.view.sel()[0].begin()
            self.view.sel().clear()
            print(a,b)
            self.view.sel().add(sublime.Region(a, b))
        return len(self.errors)

    def array(self, array_length):
        """

        :param array_length:
        :return:
        """
        self.modified_command_line.text = 'component_type component_name[' + array_length + '];'.replace('array_length',
                                                                                                         array_length)
        self.basic_completions[0].text = """for (int i = 0; i < """ + array_length + """; i++) begin
    this.component_name[i] = null;
end""".replace('array_length', array_length)
        self.basic_completions[1].text = """for (int i = 0; i < """ + array_length + """; i++) begin
    this.component_name[i] = component_type::type_id::create($psprintf(\"component_name_%0d\", i), this);
end""".replace('array_length', array_length)

    def uvm_component(self, component_type, component_name):
        """

        :param component_type:
        :param component_name:
        :return:
        """

        state = 'function_start'
        declaration_item = None
        for line_index in range(len(self.file_content)):
            self.modified_text.append(self.file_content[line_index])

            if state == 'function_start':
                for declaration_item_index in range(len(self.basic_completions)):
                    declaration_item = self.basic_completions[declaration_item_index]
                    if self.find_function(declaration_item.function_name, self.file_content[line_index]):
                        state = 'comment_start'
                        break

            else:
                if state == 'comment_start':
                    if self.find_comment(declaration_item.uvm_type.replace('component_type', component_type).replace(
                            'component_name', component_name), line_index):
                        state = 'comment_end'
                if state == 'comment_end':
                    if self.find_end_comment(line_index):
                        self.append_text(
                            declaration_item.text.replace('component_type', component_type).replace('component_name',
                                                                                                    component_name))
                        self.basic_completions.pop(declaration_item_index)
                        state = 'function_start'

            if not state == 'function_start':
                if self.find_end_function(line_index):
                    self.append_text(
                        declaration_item.comment.replace('component_type', component_type).replace('component_name',
                                                                                                   component_name))
                    self.append_text(
                        declaration_item.text.replace('component_type', component_type).replace('component_name',
                                                                                                component_name))
                    self.basic_completions.pop(declaration_item_index)
                    state = 'function_start'

        self.change_text(self.cursors_line,
                         (self.modified_command_line.comment + '\n' + self.modified_command_line.text).replace(
                             'component_type', component_type).replace('component_name', component_name))
        # self.change_text(self.cursors _line, self.modified_command_line.text.replace('component_type', component_type).replace('component_name', component_name))

    def find_function(self, function, original_line):
        """

        :param function:
        :param original_line:
        :return:
        """
        return 'super.' + function + '(' in original_line

    def find_comment(self, uvm_type, index):
        """

        :param uvm_type:
        :param index:
        :return:
        """
        self.view.run_command('goto_line', {'line': index + 1})
        self.view.run_command('move_to', {'to': 'eol'})
        position = self.view.sel()[0].begin()
        scope = self.view.scope_name(position)
        return "comment" in scope and uvm_type in self.file_content[index].title()

    def find_end_comment(self, index):
        """

        :param index:
        :return:
        """
        self.view.run_command('goto_line', {'line': index + 2})
        self.view.run_command('move_to', {'to': 'sol'})
        position = self.view.sel()[0].begin()
        scope = self.view.scope_name(position)
        return not "comment" in scope

    def find_end_function(self, index):
        """

        :param index:
        :return:
        """
        return 'endfunction' in self.file_content[index + 1]

    # FIXME: doesn't work great
    def get_indent(self, index):
        """

        :param index:
        :return:
        """
        last_line = self.modified_text[index]
        if last_line.replace(' ', '') == '':
            last_line = self.modified_text[index - 1]
        return (len(last_line) - len(last_line.lstrip())) * ' '

    def append_text(self, text):
        """

        :param text:
        :return:
        """
        indent = self.get_indent(-1)
        text = text.split('\n')
        for line in text:
            self.modified_text.append(indent + line)

    def change_text(self, index, text):
        """

        :param index:
        :param text:
        :return:
        """
        print(self.modified_text[index])
        indent = self.get_indent(index)
        text = indent+text.replace('\n', '\n' + indent)
        self.modified_text[index] = text


class DeclareComponentEventListener(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        """
        This class is created and will 'listen' to query_completions
        This means that whenever an automation panel is created this method will happened.

        :param view: the 'view' to the buffer. Basically an object associated with the tab opened by the writer
        :param prefix: the prefix that triggered this auto-completion
        :param locations: a list of the locations of the cursor
        :return: a CompletionItem that will be added to the auto-completion panel (explained later)
        """

        # FIXME: add support for multiple selection
        # If there is more than 1 cursor return nothing
        if len(locations) > 1:
            return None

        # Check the scope.
        # All the cursor must be inside a the body of a systemverilog class, can't be inside a function or a comment
        if not all(
                view.match_selector(pt, "meta.class.body.systemverilog - meta.function - comment") for pt in locations):
            return None

        # If all requirements are met return a CompletionItem
        # A command will execute for the special trigger so the function returns a command_completion
        return [
            sublime.CompletionItem.command_completion(
                "declare",                 # The trigger that will execute the command
                "declare_component",       # The name of the command that will be triggered
                {},                        # The argument passed to the command (empty for this command)
                "declare component",       # A short description for the trigger
                sublime.KIND_SNIPPET,      # The kind of trigger, mostly arbitrary and should stay sublime.KIND_SNIPPET
                details="Create uvm agent" # A description for the completion
            )
        ]
