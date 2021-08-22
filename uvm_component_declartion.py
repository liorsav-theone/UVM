import sublime
import sublime_plugin



def parse_command_line(command_line):
    """
    Function to parse a command line.
    The command line should look like the following: function_name(args); second_function(more_args)
    The ';' is used as a separator between the functions
    Using the line the cursor is at, it will parse the command and return a list of function
    Args can be anything and even more functions
    :param command_line: the command line from the buffer
    :return: a list of function gain from the command line, any warnings and errors that rose during the function
    """

    warnings = []
    errors = []
    functions_list = []

    # Split the command line using the ';' character, and strip it
    command_line = command_line.replace(' ', '').split(';')

    # This algorithm is shit, feel free to change it :)
    # It is used to add '' to all the arguments of the function on the command line
    # So that if the command line is "function_name(first, second)" it will become "function_name('first','second')""
    # The problem is what if the argument themselves are functions?

    """ Loop on the entire list
    The command is changed to a list because string is immutable in python
    The second loop iterate over every character in the command and track the number of function in the command
    The state goes up by 1 when entering a parentheses '(' and goes down by 1 when leaving a parentheses ')'
    Using this logic the first ( is replace with (' and the last ) is replace with ')
    Any , in the parentheses of the first function (when state = 1) will be replace with ','"""
    for command in command_line:

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
                if state == 0 and command[index-1]!='(':
                    function.append('\'')

            if command[index] == ',' and state == 1:
                function.append('\'')

            function.append(command[index])

            if command[index] == ',' and state == 1:
                function.append('\'')

            if command[index] == '(':
                state += 1
                if state == 1 and command[index+1]!=')':
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
    Any attribute in the text will be changed to the actual value
    for example: component_name will be changed to msg_in_agent

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
    attributes : dictionary
        a dict of all parameters and their value
        for example: 'component_name' : 'msg_in_agent'

    Methods
    -------
    init(function_name, text, uvm_type="component", comment_type="line")
        Initialize the object
    """
    attributes = {}
    def __init__(self, function_name, text, uvm_type="component", comment_type="line"):
        """
        Initialize the object and generate a comment for the declaration
        :param function_name: the name of the function that the text will be inserted to
        :param text: the text that will be inserted to declare the item
        :param uvm_type: the uvm_type of the item, determined the content of the comment
        :param comment_type: the type of the comment, can be 'line' or 'block'
        """
        self.function_name = function_name
        self.attributes = {}
        self.text = text
        self.uvm_type = uvm_type.title()
        if comment_type == "line":
            self.comment = '\n// ' + self.uvm_type
        elif comment_type == "block":
            self.comment = """\n/*------------------------------------------------------------------------------
--  """ + self.uvm_type + """
------------------------------------------------------------------------------*/"""

    def update_attributes(self, new_attributes = {}):
        """
        Update the attributes and modify the text to insert the value of the new attributes
        :param new_attributes: the name of the function that the text will be inserted to
        """
        self.attributes = dict(self.attributes, **new_attributes)
        for attribute in self.attributes:
            self.text = self.text.replace(str(attribute), str(self.attributes[attribute]))


class DeclareComponentCommand(sublime_plugin.TextCommand):
    """
    A class used to declare a uvm item.

    Basic command principles
    ----------
    sublime_plugin.TextCommand is the basic class for every command that alter text in a buffer.
    The command declare_component is automatically created by creating this class.
    The name is driven form the name of the class (CamelCase to snake_case and remove the 'command')
    When running the command the run method will be executed.

    Attributes
    ----------
    warnings : list of str
        A list of all warning rose during the command.
        Warning doesn't not prevent the command from running.
        They are used to inform the writer about special action that were taken during the command
        For example: not finding the comment needed to declare the item is a warning.
    errors : list of str
        A list of errors that rose during the command.
        Errors prevent the command from running.
        They are used to inform the writer why the command can't be executed.
        For example: invalid command line is an error.
    modified_file_content : list of str
        The text that will be inserted to the file by the end of the command
        Each line is an elem in the list
    original_file_content : str
        The content of the file before being modified.
    command_line_declaration_item : DeclarationItem
        A DeclarationItem used to modify the command_line.
        This is different from functions_declaration_items because it isn't inside a function.
    functions_declaration_items : list of DeclarationItem
        All the DeclarationItem used to declare the item.
        Include all the modification to a class methods.

    Methods
    -------

    """
    warnings = []
    errors = []
    modified_file_content = []
    original_file_content = []
    command_line_declaration_item = None
    functions_declaration_items = []

    def run(self, edit, command_lines_index_arr):
        """
        Declare a uvm component inside the environment.
        ...
        Don't call this command in any way other then using the EventListener below.
        For this command to run correctly and without errors the line the cursor is at must be a valid 'command line'.
        ...
        Command line is essentially a list of python function separated by ';'
        Valid command line looks like this: uvm_component({type}, {name}); {optional_args}
        Type is the type of the component
        Name is the name of the component
        optional_args are separated by a ';' and represent additional options
            available optional_args are: array({array_length})
                array_length is the length of the array
        ...
        This function will first parse the command line and will execute every function in the command line
        Those functions create declaration items that describe how to declare the item correctly
        Then the function will edit the text according to the deceleration items created by the list of functions

        :param edit: the object used to edit the self.view
        :param command_lines_index_arr: a list of indexes of every command line in the file
        :return: None
        """
        # Set the class attributes
        self.warnings = []
        self.errors = []

        # view is the actual 'view' to the 'buffer', simply the view is the opened tab in sublime and buffer is the
        # memory used to save the file
        # 'region' returns a part from the buffer, it takes the starting index and the end index, in this case the
        # region is from the first character to the last one (view.size() returns the size of the buffer)
        # substr return a string of content from a given region
        self.original_file_content = str(self.view.substr(sublime.Region(0, self.view.size())))

        # modified_file_content is a copy of the original
        self.modified_file_content = self.original_file_content.split('\n')

        # for every command line, starting from the last
        for command_line_index in command_lines_index_arr[::-1]:

            # Get the list of function from the command line
            list_of_functions, self.warnings, self.errors = parse_command_line(self.modified_file_content[command_line_index])

            # Check for errors
            if self.check_errors(edit, command_line_index):
                return

            # Execute every function in the list_of_functions and check for errors after each one
            for function in list_of_functions:
                exec('self.' + function)
                if self.check_errors(edit, command_line_index):
                    return

            # Edit the text according to the deceleration items created by the list of functions
            self.edit_text(edit)
            if self.check_errors(edit, command_line_index):
                return

            self.edit_command_line(edit, command_line_index)
            if self.check_errors(edit, command_line_index):
                return

        # Run the command goto_line with the argument of the index of the command line to return the cursor to the line
        # it was at before this command
        self.view.run_command("goto_line", {"line": command_lines_index_arr[0] + 1})

    def check_errors(self, edit, command_line_index):
        """
        Check for any errors in the class,
        Insert them to the file at the end of the command line and select them
        :param command_line_index: the index of the command line
        :return: 1 if there are any errors
        """
        if len(self.errors):

            # Reset any changes done to the file content
            self.view.replace(edit, sublime.Region(0, self.view.size()), self.original_file_content)

            # Using sublime command go to the end of the command line
            self.view.run_command('goto_line', {'line': command_line_index + 1})
            self.view.run_command('move_to', {'to': 'eol'})

            # Get the location of the cursor before inserting the errors
            a = self.view.sel()[0].begin()

            # The insert command insert characters in the location of the cursor
            self.view.run_command('insert', {"characters": '// Error: ' + ''.join(self.errors)})

            # Get the location of the cursor after inserting the errors
            b = self.view.sel()[0].begin()

            # Clear any other selection and select the region of the newly added errors
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(a, b))

        return len(self.errors)

    def uvm_component(self, *component_info):
        """
        Create the basic declaration items needed to declare a uvm item
        include a build and new function modifications
        :param component_info[0] : component_type - the type of the component declared
        :param component_info[1] : component_name - the name of the component declared
        :return:
        """
        if len(component_info) > 2:
            self.errors.append('Too many arguments given in uvm_component')
            return
        elif len(component_info) < 2:
            self.errors.append('Missing arguments given in uvm_component')
            return

        component_type = component_info[0]
        component_name = component_info[1]

        # Set the DeclarationItem needed to declare a basic uvm item
        # The 'component_type' and 'component_name' is later replaced with the real thing
        self.command_line_declaration_item = DeclarationItem(None, 'component_type component_name = null;')
        self.command_line_declaration_item.update_attributes({"component_type": component_type,"component_name" : component_name})

        self.functions_declaration_items = [
            DeclarationItem('new', 'this.component_name = null;'),
            DeclarationItem('build_phase',
                            'this.component_name = component_type::type_id::create(\"component_name\", this);',
                            comment_type="block")
        ]
        for declaration_item in self.functions_declaration_items:
            declaration_item.update_attributes({"component_type": component_type,"component_name" : component_name})


    def array(self, *array_info):
        """
        Change the DeclarationItem to declare an array of a given item
        Works only if the uvm_component was called before this command
        :param array_info[0]: array_length - the length of the array
        :return:
        """

        if len(array_info) > 1:
            self.errors.append('Too many arguments given in array')
            return
        elif len(array_info) < 1:
            self.errors.append('Missing arguments given in array')
            return

        array_length = array_info[0]

        self.command_line_declaration_item.text = 'component_type component_name[array_length];'
        self.command_line_declaration_item.update_attributes({"array_length": array_length})

        self.functions_declaration_items[0].text = """for (int i = 0; i < array_length; i++) begin
    this.component_name[i] = null;
end"""
        self.functions_declaration_items[1].text = """for (int i = 0; i < array_length; i++) begin
    this.component_name[i] = component_type::type_id::create($psprintf(\"component_name_%0d\", i), this);
end"""
        for declaration_item in self.functions_declaration_items:
            declaration_item.update_attributes({"array_length": array_length})


    def edit_text(self, edit):
        """
        """
        state = 'function_start'
        declaration_item = None
        found_previous_function = True
        for declaration_item_index in range(len(self.functions_declaration_items)):
            declaration_item = self.functions_declaration_items[declaration_item_index]

            if found_previous_function == False:
                self.errors.append('Could not find '+self.functions_declaration_items[declaration_item_index-1].function_name+' function')

            found_previous_function = False
            for line_index in range(len(self.modified_file_content)):
                if state == 'function_start' and self.find_function(declaration_item.function_name, self.modified_file_content[line_index]):
                    state = 'comment_start'

                if state == 'comment_start' and self.find_comment(declaration_item.uvm_type, line_index):
                    state = 'comment_end'

                if state == 'comment_start' and self.find_end_function(line_index):
                    self.insert_text(edit, line_index, declaration_item.comment + '\n' + declaration_item.text)
                    found_previous_function = True
                    state = 'function_start'

                if state == 'comment_end' and self.find_end_comment(line_index):
                    self.insert_text(edit, line_index, declaration_item.text)
                    found_previous_function = True
                    state = 'function_start'

    def edit_command_line(self, edit, command_line_index):
        """
        edit the command line according to the command_line_declaration_item
        """
        self.change_text(edit, command_line_index, self.command_line_declaration_item.text)

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
        return "comment" in scope and uvm_type in self.modified_file_content[index].title()

    def find_end_comment(self, index):
        """

        :param index:
        :return:
        """
        self.view.run_command('goto_line', {'line': index + 2})
        self.view.run_command('move_to', {'to': 'sol'})
        position = self.view.sel()[0].begin()
        scope = self.view.scope_name(position)
        return "comment" not in scope

    def find_end_function(self, index):
        """

        :param index:
        :return:
        """
        return 'endfunction' in self.modified_file_content[index + 1]

    def get_indent(self, index):
        """

        :param index:
        :return:
        """
        for last_line in self.modified_file_content[index::-1]:
            if not last_line.replace(' ', '') == '':
                return (len(last_line) - len(last_line.lstrip())) * ' '

    def insert_text(self, edit, index, text):
        """

        :param edit:
        :param index:
        :param text:
        :return:
        """
        indent = self.get_indent(index)
        text = indent + text.replace('\n', '\n' + indent)
        for line in text.split('\n')[::-1]:
            self.modified_file_content.insert(index + 1, line)
        self.view.replace(edit, sublime.Region(0, self.view.size()), '\n'.join(self.modified_file_content))


    def change_text(self, edit, index, text):
        """

        :param edit:
        :param index:
        :param text:
        :return:
        """
        indent = self.get_indent(index)
        text = indent + text.replace('\n', '\n' + indent)
        self.modified_file_content[index] = text
        self.view.replace(edit, sublime.Region(0, self.view.size()), '\n'.join(self.modified_file_content))


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

        # Check the scope.
        # All the cursor must be inside a the body of a systemverilog class, can't be inside a function or a comment
        if not all(
                view.match_selector(pt, "meta.class.body.systemverilog - meta.function - comment") for pt in locations):
            return None

        # Get the row of every cursor
        command_lines_index_arr = []
        for pt in locations:
            command_lines_index_arr.append(view.rowcol(pt)[0])

        # If all requirements are met return a CompletionItem
        # A command will execute for the special trigger so the function returns a command_completion
        return [
            sublime.CompletionItem.command_completion(
                "declare",                                             # The trigger that will execute the command
                "declare_component",                                   # The name of the command that will be triggered
                {'command_lines_index_arr': command_lines_index_arr},  # The argument passed to the command (empty for this command)
                "declare component",                                   # A short description for the trigger
                sublime.KIND_SNIPPET,                                  # The kind of trigger, mostly arbitrary and should stay sublime.KIND_SNIPPET
                details="Create uvm agent"                             # A description for the completion
            )
        ]
