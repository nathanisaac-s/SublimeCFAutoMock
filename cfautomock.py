import sublime, sublime_plugin
import math
import re
import textwrap

class cfautomockCommand(sublime_plugin.TextCommand):
    method_name_re = re.compile("name\s*\=\s*[\"\']", re.IGNORECASE)
    access_level_re = re.compile("access\s*\=\s*[\"\']", re.IGNORECASE)
    var_name_re = re.compile("(?<=variables\.).*?(?=\.)", re.IGNORECASE)
    component_args_re = re.compile("(?<=[\(])[^;]*(?=\)\;)", re.IGNORECASE)
    component_method_name_re = re.compile(r'(?<=\.)[^\.]*?(?=[\r\n]?\()', re.IGNORECASE)
    supported_argument_types = [
            'any',
            'array',
            'binary',
            'boolean',
            'date',
            'guid',
            'numeric',
            'query',
            'string',
            'struct',
            'uuid',
            'xml' ]

    type_values = { 
            'any' : '\"\"', 
            'array' : '[]', 
            'binary' : 'toBinary(toBase64(\"a\"))', 
            'boolean' : 'true', 
            'date' : 'Now()', 
            'guid' : 'CreateUUID()', 
            'numeric' : '0', 
            'query' : 'QueryNew(\"col\",\"int\")', 
            'string' : '\"\"', 
            'struct' : '{}', 
            'uuid' : 'CreateUUID()', 
            'xml' : '\"<a></a>\"' }

    def get_dummy_value_for_type(self, cftype):
        return self.type_values[cftype]

    def get_arguments(self, method, required_only=None):
        if not required_only: #safe default value practice
            required_only = False

        def get_type_and_name(string_to_tokenize):
            tokens = re.sub( "(<\s*cfargument\s*|\\|>)\s*", "", view_substr, re.IGNORECASE)

            for attr_name, attr_value in re.findall("([a-zA-Z]+)\s*=\s*[\'\"]([a-zA-Z-_]+)[\'\"]", tokens):
                if attr_name == "name":
                    name_value = attr_value
                elif attr_name == "type":
                    type_value = attr_value

            return name_value, type_value

        cfarguments = self.view.find_all("<cfargument[\s\S]*?>")
        required_attr_re = re.compile("required\s*\=\s*[\"\'](true|yes|1)", re.IGNORECASE)

        arguments = []
        for view_substr in [ self.view.substr(argument) for argument in cfarguments ]:
            if required_only:
                if argument.intersects(method) and required_attr_re.search(view_substr):
                    name_value, type_value = get_type_and_name(view_substr)

                    # store the supported argument name and type
                    if type_value.lower() in self.supported_argument_types:
                        arguments.append((name_value, type_value.lower()))
            else:
                if argument.intersects(method):
                    name_value, type_value = get_type_and_name(view_substr)

                    # store the supported argument name and type
                    if type_value.lower() in self.supported_argument_types:
                        arguments.append((name_value, type_value.lower()))

        return arguments


    def get_header_stats(self):
        f = self.view

        return textwrap.dedent("""
            CFAutoMock
            
            General Stats:
            ==========================================================================================================================
            File: {file_name}
            Size: ~{kb}Kb ({size} bytes)
            """.format( file_name=f.file_name(), kb=f.size()/1024, size=f.size()) )


    def get_method_counts(self, _all_methods):
        #loop through functions and find all private and remote functions
        pub_count, priv_count, remote_count, pkg_count = 0, 0, 0, 0

        smarter_access_re = re.compile("access\s*\=\s*[\"\'](public|remote|private|package)[\"\']", re.IGNORECASE)
        access_public_re = re.compile("access\s*\=\s*[\"\'](public)[\"\']", re.IGNORECASE)
        access_remote_re = re.compile("access\s*\=\s*[\"\'](remote)[\"\']", re.IGNORECASE)
        access_private_re = re.compile("access\s*\=\s*[\"\'](private)[\"\']", re.IGNORECASE)
        access_package_re = re.compile("access\s*\=\s*[\"\'](package)[\"\']", re.IGNORECASE)

        for method in _all_methods:
            #TODO one regex, not four
            for line in self.view.split_by_newlines(method):
                if access_public_re.search(self.view.substr(line)):
                    pub_count += 1
                elif access_private_re.search(self.view.substr(line)):
                    priv_count += 1
                elif access_remote_re.search(self.view.substr(line)):
                    remote_count += 1
                elif access_package_re.search(self.view.substr(line)):
                    pkg_count += 1

        return textwrap.dedent("""
            Methods
            \t{public} Public
            \t{private} Private
            \t{remote} Remote
            \t{pkg} Package
            ==========================================================================================================================
            """.format( public=pub_count, private=priv_count, remote=remote_count, pkg=pkg_count) )

    def populate_new_tab(self, text, _edit):
        #send to new file
        new_window = self.view.window()
        new_window.run_command("new_file")
        view = new_window.active_view()
        view.insert(_edit, 0, text)


    def get_method_details(self, method_lines):
        method_details = { 'Name' : '', 'Access' : 'public' }

        # get the method name and access
        for line in method_lines:                
            if not len(method_details['Name']) and self.method_name_re.search(self.view.substr(line)):
                for splitted_item in self.view.substr(line).split():
                    if self.method_name_re.search(splitted_item):
                        method_details['Name'] = re.sub(">", "", splitted_item)
                        method_details['Name'] = re.sub("[\'\" ]", "", method_details['Name'])
                        method_details['Name'] = re.sub("name\s*\=\s*", "", method_details['Name'])
                    elif self.access_level_re.search(splitted_item):
                        # DAE copy and paste easier than DRY?
                        method_details['Access'] = re.sub(">", "" ,splitted_item).lower()
                        method_details['Access'] = re.sub("[\'\" ]", "", method_details['Access'])
                        method_details['Access'] = re.sub("access\s*\=\s*", "", method_details['Access'])

        return method_details


    def build_stub_test(self, _method):
        method_line_by_line = self.view.split_by_newlines(_method)
        method_details = self.get_method_details(method_line_by_line)

        # gather all arguments
        arguments = self.get_arguments(_method)

        unit_test = ""
        unit_test += "\n\n\t<cffunction name=\"" + method_details['Name'] + "_ValidArgs_ReturnsSuccess\" access=\"public\">"
        unit_test += "\n\t\t<cfscript>"
        unit_test += "\n\t\t\tvar Obj = __GetComponentToBeTested();"
        unit_test += "\n\t\t\tvar expected  = \"\";"
        if method_details['Access'] == "private":
            unit_test += "\n\t\t\tmakePublic(Obj, \"" + method_details['Name'] + "\");"

        # mock variables stored components and their methods
        variable_scope_dependencies = re.findall(r'variables\.[^\.]*?\.[^\(]*?\([^\;]*?\;', self.view.substr(_method), re.IGNORECASE)

        components_to_mock = []
        component_methods_to_mock = []

        for dependency_to_mock in variable_scope_dependencies:
            name_of_component_to_mock = self.var_name_re.findall(dependency_to_mock)
            name_of_method_to_mock = self.component_method_name_re.findall(dependency_to_mock)
            args_for_component_method_to_mock = self.component_args_re.findall(dependency_to_mock)

            if args_for_component_method_to_mock[0]:
                num_of_args_to_mock = len(args_for_component_method_to_mock[0].strip().split(','))
            else:
                num_of_args_to_mock = 0

            if name_of_component_to_mock[0] and name_of_method_to_mock[0]:
                # TODO i think it's safe to just set these values, not if them.
                if { 'ComponentName' : name_of_component_to_mock[0], 
                        'Scope' : 'variables'} not in components_to_mock:
                    components_to_mock.append({
                        'ComponentName' : name_of_component_to_mock[0], 
                        'Scope' : 'variables'})

                # TODO i think it's safe to just set these values, not if them.
                if { 'ComponentName' : name_of_component_to_mock[0], 
                        'MethodName' : name_of_method_to_mock[0].strip(), 
                        'NumberOfArgs' : num_of_args_to_mock 
                        } not in component_methods_to_mock:
                    component_methods_to_mock.append({'ComponentName' : name_of_component_to_mock[0], 'MethodName' : name_of_method_to_mock[0].strip(), 'NumberOfArgs' : num_of_args_to_mock })
            else:
                unit_test += "\n\t\t\t/* Failed to mock: " + dependency_to_mock + "*/"

        # write mocked methods
        for component in components_to_mock:
            unit_test += "\n\n\t\t\tvar " + component['ComponentName'] + "Mock = mock();"
            
            for component_method in component_methods_to_mock:
                if component['ComponentName'] == component_method['ComponentName']:
                    unit_test += "\n\t\t\tvar " + component_method['MethodName'] + "Return = \"\";"
                    unit_test += "\n\t\t\t" + component['ComponentName'] + "Mock." + component_method['MethodName'] + "(" \
                            + ','.join( ["\"{any}\"" for a in range(0, component_method['NumberOfArgs'])]) \
                            + ").returns(" + component_method['MethodName'] + "Return);"
                    # ^wtf

            unit_test += "\n\t\t\tinjectProperty(Obj, \"" + component['ComponentName'] + "\", " + component['ComponentName'] + "Mock, \"" + component['Scope'] + "\");"

        # write actual 
        unit_test += "\n\n\t\t\tvar actual = Obj." + method_details['Name']
        unit_test += "\n\t\t\t(" 
        
        unit_test += ", ".join([ 
            "\n\t\t\t\t" + name_arg + " = " + self.get_dummy_value_for_type(type_arg)
                for name_arg, type_arg in arguments ])

        unit_test += textwrap.dedent("""
            \t\t\t\t);

            \t\t\tAssert(actual eq expected,\"Expected something but got something else\");
            \t\t</cfscript>
            \t</cffunction>""")

        return unit_test

    
    def built_complete_test(self, _method):
        unit_test = ""
        method_line_by_line = self.view.split_by_newlines(_method)
        method_details = self.get_method_details(method_line_by_line)

        # create missing arg unit test
        arguments = self.get_arguments(_method, True)

        for argument in arguments:
            unit_test = "" #is this a bug?
            unit_test += "\n\n\t<cffunction name=\"" + method_details['Name'] + "_MissingArg_" + argument[0] + "_ReturnsException\" access=\"public\" mxunit:expectedException=\"Coldfusion.runtime.MissingArgumentException\">"

            if method_details['Access'] == "private" or method_details['Access'] == "package":
                unit_test += "\n\t\t<cfset makePublic(\"" + method_details['Name'] + "\") />"

            unit_test += "\n\t\t<cfset variables.ComponentToBeTested." + method_details['Name']
            unit_test += "\n\t\t(" 
            
            other_arguments = list(arguments) #deep copy? this is confusing.
            other_arguments.remove(argument) #this isn't programming, it's banging a keyboard

            unit_test += ", ".join([ 
                "\n\t\t\t" + name_arg + " = " + self.get_dummy_value_for_type(type_arg)
                    for name_arg, type_arg in other_arguments ])

            unit_test += "\n\t\t) />"
            unit_test += "\n\t</cffunction>"

        return unit_test


    def get_actual_return_msg(self, _all_methods, test_stubs, test_completes):
        # TODO fucking string.format, how does it work?
        return_msg = self.get_header_stats() + self.get_method_counts(_all_methods)
        # TODO move this into a file, or something. it's stupid in code.
        # is this a bug? should it  hae an that second unclosed `cfcomponent` tag?
        pub_methods = textwrap.dedent("""
            <cfcomponent extends=\"unittests.myTestCasesConfig\">

            \t<!--------------------------------------------------------------------------
            \tSection: Public methods
            \t--------------------------------------------------------------------------->

            \t<cffunction name=\"Setup\" access=\"public\">
            \t\t<cfset variables.ComponentToBeTested = __GetComponentToBeTested() />
            \t</cffunction>

            \t<cffunction name=\"TearDown\" access=\"public\">
            \t\t<cfset StructDelete(variables, \"ComponentToBeTested\") />
            \t</cffunction>



            \t<!--------------------------------------------------------------------------
            \tSection: Unit Test Stubs - These unit tests must be finished by the end user.
            \t--------------------------------------------------------------------------->
            <cfcomponent extends=\"unittests.myTestCasesConfig\">

            \t<!--------------------------------------------------------------------------
            \tSection: Public methods
            \t--------------------------------------------------------------------------->

            \t<cffunction name=\"Setup\" access=\"public\">
            \t\t<cfset variables.ComponentToBeTested = __GetComponentToBeTested() />
            \t</cffunction>

            \t<cffunction name=\"TearDown\" access=\"public\">
            \t\t<cfset StructDelete(variables, \"ComponentToBeTested\") />
            \t</cffunction>



            \t<!--------------------------------------------------------------------------
            \tSection: Unit Test Stubs - These unit tests must be finished by the end user.
            \t--------------------------------------------------------------------------->
            """)
        priv_methods = textwrap.dedent("""


            \t<!--------------------------------------------------------------------------
            \tSection: Private methods
            \t--------------------------------------------------------------------------->

            \t<cffunction name=\"__GetComponentToBeTested\" access=\"private\">
            \t\t<cfreturn CreateObject(\"component\",\"path.to.ComponentToBeTested\") />
            \t</cffunction>

            </cfcomponent>
            """)

        return_msg += pub_methods
        return_msg += test_stubs
        return_msg += "\n\n\n\t<!--------------------------------------------------------------------------"
        return_msg += "\n\tSection: Complete Unit Tests"
        return_msg += "\n\t--------------------------------------------------------------------------->"
        return_msg += test_completes
        return_msg += priv_methods

        return return_msg


    def run(self, edit):
        all = self.view.find_all("[\s\S]*")
        self.view.add_regions("AllContent", all, "source", sublime.HIDDEN)
        g = self.view.get_regions("AllContent")
        for allregion in g:
            h = len(self.view.substr(allregion))
        
        #get all functions
        #TODO holy crap this thing loops over the exact same shit about 10 times
        all_methods = self.view.find_all("<cffunction[\s\S]*?<\/cffunction>", sublime.IGNORECASE)
        
        stubbed_tests = ""
        completed_tests = ""

        # loop through methods and begin writing unit tests 
        for method in all_methods:
            stubbed_tests += self.build_stub_test(method)
            completed_tests += self.built_complete_test(method)
        
        return_msg = self.get_actual_return_msg( all_methods, stubbed_tests, completed_tests )

        self.populate_new_tab(return_msg, edit)
