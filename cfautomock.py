import sublime, sublime_plugin
import math
import re
import textwrap

class cfautomockCommand(sublime_plugin.TextCommand):
    ascii_hr = "=========================================================================================================================="
    method_name_re = re.compile("name\s*\=\s*[\"\']", re.IGNORECASE)
    access_level_re = re.compile("access\s*\=\s*[\"\']", re.IGNORECASE)
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

    def get_dummy_value_for_type(self, cftype):
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
        return type_values[cftype]

    def get_arguments(self, method, required_only=False):
        arguments = []
        cfarguments = self.view.find_all("<cfargument[\s\S]*?>")
        name_attr_re = re.compile("name\s*\=\s*[\"\']", re.IGNORECASE)
        type_attr_re = re.compile("type\s*\=\s*[\"\']", re.IGNORECASE)
        required_attr_re = re.compile("required\s*\=\s*[\"\'](true|yes|1)", re.IGNORECASE)
        single_quote_re = re.compile("[\'\" ]", re.IGNORECASE)

        for argument in cfarguments:
            if required_only:
                if argument.intersects(method) and required_attr_re.search(self.view.substr(argument)):
                    tokens = re.sub( "(<\s*cfargument\s*|\\|>)\s*", "", self.view.substr(argument), re.IGNORECASE)

                    for attr_name, attr_value in re.findall("([a-zA-Z]+)\s*=\s*[\'\"]([a-zA-Z-_]+)[\'\"]", tokens):
                        if attr_name == "name":
                            name_value = attr_value
                        if attr_name == "type":
                            type_value = attr_value

                    # store the supported argument name and type
                    if type_value.lower() in self.supported_argument_types:
                        arguments.append([name_value, type_value.lower()])
            else:
                if argument.intersects(method):
                    tokens = re.sub( "(<\s*cfargument\s*|\\|>)\s*", "", self.view.substr(argument), re.IGNORECASE)

                    for attr_name, attr_value in re.findall("([a-zA-Z]+)\s*=\s*[\'\"]([a-zA-Z-_]+)[\'\"]", tokens):
                        if attr_name == "name":
                            name_value = attr_value
                        if attr_name == "type":
                            type_value = attr_value

                    # store the supported argument name and type
                    if type_value.lower() in self.supported_argument_types:
                        arguments.append([name_value, type_value.lower()])

        return arguments

    def get_header_stats(self):
        f = self.view

        return textwrap.dedent("""
            CFAutoMock
            
            General Stats:
            ==========================================================================================================================
            File: {file_name}
            Size: ~{kb}Kb ({size} bytes)
            """.format( file_name=str(f.file_name()), kb=str(f.size()/1024), size=str(f.size())) )

    def get_method_counts(self, _all_methods):
        #loop through functions and find all private and remote functions
        public_count, private_count, remote_count, pkg_count = 0, 0, 0, 0

        smarter_access_re = re.compile("access\s*\=\s*[\"\'](public|remote|private|package)[\"\']", re.IGNORECASE)
        access_public_re = re.compile("access\s*\=\s*[\"\'](public)[\"\']", re.IGNORECASE)
        access_remote_re = re.compile("access\s*\=\s*[\"\'](remote)[\"\']", re.IGNORECASE)
        access_private_re = re.compile("access\s*\=\s*[\"\'](private)[\"\']", re.IGNORECASE)
        access_package_re = re.compile("access\s*\=\s*[\"\'](package)[\"\']", re.IGNORECASE)

        for method in _all_methods:
            #TODO one regex, not four
            for line in self.view.split_by_newlines(method):
                if access_public_re.search(self.view.substr(line)):
                    public_count += 1
                elif access_private_re.search(self.view.substr(line)):
                    private_count += 1
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
            """.format(
                public=public_count, private=private_count, remote=remote_count, pkg=pkg_count) )

    def populate_new_tab(self, text, _edit):
        #send to new file
        new_window = self.view.window()
        new_window.run_command("new_file")
        view = new_window.active_view()
        view.insert(_edit, 0, text)


    def build_stub_test(self, _method):
        method_details = { 'Name' : '', 'Access' : 'public' }
        method_line_by_line = self.view.split_by_newlines(_method)

        # get the method name and access
        for line in method_line_by_line:                
            if not len(method_details['Name']) and self.method_name_re.search(self.view.substr(line)):
                for splitted_item in self.view.substr(line).split():
                    if self.method_name_re.search(splitted_item):
                        method_details['Name'] = re.sub(">", "", splitted_item)
                        method_details['Name'] = re.sub("[\'\" ]", "", method_details['Name'])
                        method_details['Name'] = re.sub("name\s*\=\s*", "", method_details['Name'])
                    elif self.access_level_re.search(splitted_item):
                        method_details['Access'] = re.sub(">", "", splitted_item.lower())
                        method_details['Access'] = re.sub("[\'\" ]", "", method_details['Access'])
                        method_details['Access'] = re.sub("access\s*\=\s*", "", method_details['Access'])
    
        # gather all arguments
        arguments = self.get_arguments(_method)

        unit_test = ""
        unit_test += "\n\n\t<cffunction name=\"" + str(method_details['Name']) + "_ValidArgs_ReturnsSuccess\" access=\"public\">"
        unit_test += "\n\t\t<cfscript>"
        unit_test += "\n\t\t\tvar Obj = __GetComponentToBeTested();"
        unit_test += "\n\t\t\tvar expected  = \"\";"
        if str(method_details['Access']) == "private":
            unit_test += "\n\t\t\tmakePublic(Obj, \"" + str(method_details['Name']) + "\");"

        # mock variables stored components and their methods
        variable_scop_dependencies = re.findall(r'variables\.[^\.]*?\.[^\(]*?\([^\;]*?\;', self.view.substr(_method), re.IGNORECASE)

        components_to_mock = []
        component_methods_to_mock = []
        for dependency_to_mock in variable_scop_dependencies:
            name_of_component_to_mock = re.findall(r'(?<=variables\.).*?(?=\.)', dependency_to_mock, re.IGNORECASE)
            name_of_method_to_mock = re.findall(r'(?<=\.)[^\.]*?(?=[\r\n]?\()', dependency_to_mock, re.IGNORECASE)
            args_for_component_method_to_mock = re.findall(r'(?<=[\(])[^;]*(?=\)\;)', dependency_to_mock, re.IGNORECASE)
            if args_for_component_method_to_mock[0]:
                number_of_args_for_component_method_to_mock = len(args_for_component_method_to_mock[0].strip().split(','))
            else:
                number_of_args_for_component_method_to_mock = 0

            if name_of_component_to_mock[0] and name_of_method_to_mock[0]:
                if { 'ComponentName' : name_of_component_to_mock[0], 
                        'Scope' : 'variables'} not in components_to_mock:
                    components_to_mock.append({
                        'ComponentName' : name_of_component_to_mock[0], 
                        'Scope' : 'variables'})

                if { 'ComponentName' : name_of_component_to_mock[0], 
                        'MethodName' : name_of_method_to_mock[0].strip(), 
                        'NumberOfArgs' : number_of_args_for_component_method_to_mock 
                        } not in component_methods_to_mock:
                    component_methods_to_mock.append({'ComponentName' : name_of_component_to_mock[0], 'MethodName' : name_of_method_to_mock[0].strip(), 'NumberOfArgs' : number_of_args_for_component_method_to_mock })
            else:
                unit_test += "\n\t\t\t/* Failed to mock: " + str(dependency_to_mock) + "*/"

        # write mocked methods
        for component in components_to_mock:
            unit_test += "\n\n\t\t\tvar " + str(component['ComponentName']) + "Mock = mock();"
            
            for component_method_to_mock in component_methods_to_mock:
                if component['ComponentName'] == component_method_to_mock['ComponentName']:
                    unit_test += "\n\t\t\tvar " + str(component_method_to_mock['MethodName']) + "Return = \"\";"

            #holy shit this guy is retarded
            #TODO merge these two loops
            for component_method_to_mock in component_methods_to_mock:
                if component['ComponentName'] == component_method_to_mock['ComponentName']:
                    unit_test += "\n\t\t\t" + str(component['ComponentName']) + "Mock." + str(component_method_to_mock['MethodName']) + "(" + ','.join(["\"{any}\"" for a in range(0,component_method_to_mock['NumberOfArgs'])]) + ").returns(" + str(component_method_to_mock['MethodName']) + "Return);"

            unit_test += "\n\t\t\tinjectProperty(Obj, \"" + str(component['ComponentName']) + "\", " + str(component['ComponentName']) + "Mock, \"" + str(component['Scope'])  + "\");"

        # write actual 
        unit_test += "\n\n\t\t\tvar actual = Obj." + str(method_details['Name'])
        unit_test += "\n\t\t\t(" 
        
        #TODO fucking list comprehensions, how do they work
        for oindex, argument in enumerate(arguments):
            unit_test += "\n\t\t\t\t" + argument[0] + " = " + self.get_dummy_value_for_type(argument[1])
            if oindex + 1 < len(arguments):
                #TODO fucking .join, how does it work
                unit_test += ","                    

        unit_test += "\n\t\t\t);"
        unit_test += "\n\n\t\t\tAssert(actual eq expected,\"Expected something but got something else\");"
        unit_test += "\n\t\t</cfscript>"
        unit_test += "\n\t</cffunction>"

        return unit_test

    
    def built_complete_test(self, _method):
        unit_test = ""
        method_details = { 'Name' : '', 'Access' : 'public' }
        method_line_by_line = self.view.split_by_newlines(_method)
        self.access_level_re = re.compile("access\s*\=\s*[\"\']", re.IGNORECASE)

        # get the method name and access
        for line in method_line_by_line:                
            if not len(method_details['Name']) and self.method_name_re.search(self.view.substr(line)):
                for splitted_item in self.view.substr(line).split():
                    if self.method_name_re.search(splitted_item):
                        method_details['Name'] = re.sub(">","",str(splitted_item))
                        method_details['Name'] = re.sub("[\'\" ]","",str(method_details['Name']))
                        method_details['Name'] = re.sub("name\s*\=\s*","",str(method_details['Name']))
                    elif self.access_level_re.search(splitted_item):
                        # DAE copy and paste easier than DRY?
                        method_details['Access'] = re.sub(">","",str(splitted_item).lower())
                        method_details['Access'] = re.sub("[\'\" ]","",str(method_details['Access']))
                        method_details['Access'] = re.sub("access\s*\=\s*","",str(method_details['Access']))

        # create missing arg unit test
        arguments = self.get_arguments(_method, True)

        for argument in arguments:
            unit_test = "" #is this a bug?
            unit_test += "\n\n\t<cffunction name=\"" + str(method_details['Name']) + "_MissingArg_" + argument[0] + "_ReturnsException\" access=\"public\" mxunit:expectedException=\"Coldfusion.runtime.MissingArgumentException\">"
            if str(method_details['Access']) == "private" or str(method_details['Access']) == "package":
                unit_test += "\n\t\t<cfset makePublic(\"" + str(method_details['Name']) + "\") />"

            unit_test += "\n\t\t<cfset variables.ComponentToBeTested." + str(method_details['Name'])
            unit_test += "\n\t\t(" 
            
            other_arguments = list(arguments)
            other_arguments.remove(argument) #this isn't programming, it's banging a keyboard

            for oindex, other_arg in enumerate(other_arguments):
                unit_test += "\n\t\t\t" + other_arg[0] + " = " + self.get_dummy_value_for_type(other_arg[1])
                if oindex + 1 < len(other_arguments):
                    # TODO ...and, again, a simple join
                    unit_test += ","                    

            unit_test += "\n\t\t) />"
            unit_test += "\n\t</cffunction>"

        return unit_test


    def get_actual_return_msg(self, _all_methods, test_stubs, test_completes):
        # fucking string.format, how does it work?
        return_msg = self.get_header_stats() + self.get_method_counts(_all_methods)
        return_msg += "\n<cfcomponent extends=\"unittests.myTestCasesConfig\">"
        return_msg += "\n\n\t<!--------------------------------------------------------------------------"
        return_msg += "\n\tSection: Public methods"
        return_msg += "\n\t--------------------------------------------------------------------------->"
        return_msg += "\n\n\t<cffunction name=\"Setup\" access=\"public\">"
        return_msg += "\n\t\t<cfset variables.ComponentToBeTested = __GetComponentToBeTested() />"
        return_msg += "\n\t</cffunction>"
        return_msg += "\n\n\t<cffunction name=\"TearDown\" access=\"public\">"
        return_msg += "\n\t\t<cfset StructDelete(variables, \"ComponentToBeTested\") />"
        return_msg += "\n\t</cffunction>\n"
        return_msg += "\n\n\n\t<!--------------------------------------------------------------------------"
        return_msg += "\n\tSection: Unit Test Shells - These unit tests must be finished by the end user."
        return_msg += "\n\t--------------------------------------------------------------------------->"
        return_msg += test_stubs
        return_msg += "\n\n\n\t<!--------------------------------------------------------------------------"
        return_msg += "\n\tSection: Complete Unit Tests"
        return_msg += "\n\t--------------------------------------------------------------------------->"
        return_msg += test_completes
        return_msg += "\n\n\n\t<!--------------------------------------------------------------------------"
        return_msg += "\n\tSection: Private methods"
        return_msg += "\n\t--------------------------------------------------------------------------->"
        return_msg += "\n\n\t<cffunction name=\"__GetComponentToBeTested\" access=\"private\">"
        return_msg += "\n\t\t<cfreturn CreateObject(\"component\",\"path.to.ComponentToBeTested\") />"
        return_msg += "\n\t</cffunction>"
        return_msg += "\n\n</cfcomponent>"

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

        # #############################
        # STUB TESTS
        # #############################

        # loop through methods and begin writing unit tests 
        for method in all_methods:
            stubbed_tests += self.build_stub_test(method)

        # #############################
        # COMPLETE UNIT TESTS
        # #############################

        # loop through methods and begin writing unit tests 
        for method in all_methods:
            completed_tests += self.built_complete_test(method)
        
        return_msg = self.get_actual_return_msg( all_methods, stubbed_tests, completed_tests )

        self.populate_new_tab(return_msg, edit)

