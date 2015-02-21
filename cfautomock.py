import sublime, sublime_plugin
import math
import re

class cfautomockCommand(sublime_plugin.TextCommand):
    
    def run(self, edit):

        def get_dummy_value_for_type(cftype):
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

        def get_arguments(method, required_only=False):
            arguments = []

            cfarguments = self.view.find_all("<cfargument[\s\S]*?>")

            name_attr_re = re.compile("name\s*\=\s*[\"\']", re.IGNORECASE)
            type_attr_re = re.compile("type\s*\=\s*[\"\']", re.IGNORECASE)
            required_attr_re = re.compile("required\s*\=\s*[\"\'](true|yes|1)", re.IGNORECASE)
            single_quote_re = re.compile("[\'\" ]", re.IGNORECASE)
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

            for argindex, argument in enumerate(cfarguments):
                if required_only == True:
                    if argument.intersects(method) and required_attr_re.search(self.view.substr(argument)):
                        for key in self.view.substr(argument).split():
                            # remove quotes and dbl quotes
                            value = re.sub("[\'\" ]", "", str(key))

                            if name_attr_re.search(key):
                                # remove name=
                                name_value = re.sub("name\=", "", str(value))

                            if type_attr_re.search(key):
                                # remove type=
                                type_value = re.sub("type\=", "", str(value))

                        # store the supported argument name and type
                        if type_value.lower() in supported_argument_types:
                            arguments.append([name_value, type_value.lower()])
                else:
                    if argument.intersects(method):
                        for key in self.view.substr(argument).split():
                            # remove quotes and dbl quotes
                            value = re.sub("[\'\" ]", "", str(key))

                            if name_attr_re.search(key):
                                # remove name=
                                name_value = re.sub("name\=", "", str(value))

                            if type_attr_re.search(key):
                                # remove type=
                                type_value = re.sub("type\=", "", str(value)) 
                        
                        # store the supported argument name and type
                        if type_value.lower() in supported_argument_types:
                            arguments.append([name_value, type_value.lower()])

            return arguments

        #write general stats
        f = self.view
        # fucking string.format(), how does it work?
        return_msg = ""
        return_msg = "\nCFAutoMock \n\nGeneral Stats:\n==========================================================================================================================\n"
        return_msg += "File: "+str(f.file_name())+"\nSize: ~"+str(f.size()/1024)+"Kb ("+str(f.size())+" bytes)\n"
        all = self.view.find_all("[\s\S]*")
        self.view.add_regions("AllContent", all, "source", sublime.HIDDEN)
        g = self.view.get_regions("AllContent")
        for allregion in g:
            h = len(self.view.substr(allregion))
        
        #get all functions
        all_methods = self.view.find_all("<cffunction[\s\S]*?<\/cffunction>", sublime.IGNORECASE)

        public_method_indices = []
        private_method_indices = []
        remote_method_indices = []
        package_method_indices = []

        #loop through functions and find all private and remote functions
        for idx, method in enumerate(all_methods):
            method_line_by_line = self.view.split_by_newlines(method)
            access_public_re = re.compile("access\s*\=\s*[\"\'](public)[\"\']", re.IGNORECASE)
            access_remote_re = re.compile("access\s*\=\s*[\"\'](remote)[\"\']", re.IGNORECASE)
            access_private_re = re.compile("access\s*\=\s*[\"\'](private)[\"\']", re.IGNORECASE)
            access_package_re = re.compile("access\s*\=\s*[\"\'](package)[\"\']", re.IGNORECASE)

            for line in method_line_by_line:
                found_access_public = access_public_re.search(self.view.substr(line))
                if found_access_public:
                    public_method_indices.append(idx)                    
            
            for line in method_line_by_line:
                found_access_remote = access_remote_re.search(self.view.substr(line))
                if found_access_remote:
                    remote_method_indices.append(idx)                    

            for line in method_line_by_line:
                found_access_private = access_private_re.search(self.view.substr(line))
                if found_access_private:
                    private_method_indices.append(idx)
            
            for line in method_line_by_line:
                found_access_package = access_package_re.search(self.view.substr(line))
                if found_access_package:
                    package_method_indices.append(idx)


        return_msg += "Methods:\n\t" + str(len(public_method_indices)) + " Public\n\t" + str(len(private_method_indices)) + " Private\n\t" + str(len(remote_method_indices)) + " Remote\n\t" + str(len(package_method_indices)) + " Package"
        return_msg += "\n==========================================================================================================================\n"
        
        shell_unit_tests_collection = ""
        complete_unit_tests_collection = ""
        unit_tests_total= 0
    
        

        # #############################
        # UNIT TEST SHELLS  #TODO rename these because a "shell" is a place you run "shell commands"
        # #############################

        # loop through methods and begin writing unit tests 
        for idx, method in enumerate(all_methods):

            method_details = { 'Name' : '', 'Access' : 'public' }
            method_line_by_line = self.view.split_by_newlines(method)
            method_name_re = re.compile("name\s*\=\s*[\"\']", re.IGNORECASE)
            access_level_re = re.compile("access\s*\=\s*[\"\']", re.IGNORECASE)
            functions_re = re.compile("(?<!response)(?<!result)\.[A-Za-z\d_]+\(", re.IGNORECASE)

            # get the method name and access
            for line in method_line_by_line:                
                if not len(method_details['Name']) and method_name_re.search(self.view.substr(line)):
                    for splitted_item in self.view.substr(line).split():
                        if method_name_re.search(splitted_item):
                            method_details['Name'] = re.sub(">", "", str(splitted_item))
                            method_details['Name'] = re.sub("[\'\" ]", "", str(method_details['Name']))
                            method_details['Name'] = re.sub("name\=", "", str(method_details['Name']))
                        elif access_level_re.search(splitted_item):
                            method_details['Access'] = re.sub(">", "", str(splitted_item).lower())
                            method_details['Access'] = re.sub("[\'\" ]", "", str(method_details['Access']))
                            method_details['Access'] = re.sub("access\=", "", str(method_details['Access']))

        
            # gather all arguments
            arguments = get_arguments(method)

            unit_test = ""
            unit_test += "\n\n\t<cffunction name=\"" + str(method_details['Name']) + "_ValidArgs_ReturnsSuccess\" access=\"public\">"
            unit_test += "\n\t\t<cfscript>"
            unit_test += "\n\t\t\tvar Obj = __GetComponentToBeTested();"
            unit_test += "\n\t\t\tvar expected  = \"\";"
            if str(method_details['Access']) == "private":
                unit_test += "\n\t\t\tmakePublic(Obj, \"" + str(method_details['Name']) + "\");"

            # mock variables stored components and their methods
            variable_scop_dependencies = re.findall(r'variables\.[^\.]*?\.[^\(]*?\([^\;]*?\;', self.view.substr(method), re.IGNORECASE)

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
                    if {'ComponentName' : name_of_component_to_mock[0], 'Scope' : 'variables'} not in components_to_mock:
                        components_to_mock.append({'ComponentName' : name_of_component_to_mock[0], 'Scope' : 'variables'})

                    if {'ComponentName' : name_of_component_to_mock[0], 'MethodName' : name_of_method_to_mock[0].strip(), 'NumberOfArgs' : number_of_args_for_component_method_to_mock } not in component_methods_to_mock:
                        component_methods_to_mock.append({'ComponentName' : name_of_component_to_mock[0], 'MethodName' : name_of_method_to_mock[0].strip(), 'NumberOfArgs' : number_of_args_for_component_method_to_mock })

                else:
                    unit_test += "\n\t\t\t/* Failed to mock: " + str(dependency_to_mock) + "*/"

            # write mocked methods
            for component in components_to_mock:
                unit_test += "\n\n\t\t\tvar " + str(component['ComponentName']) + "Mock = mock();"
                
                for component_method_to_mock in component_methods_to_mock:
                    if component['ComponentName'] == component_method_to_mock['ComponentName']:
                        unit_test += "\n\t\t\tvar " + str(component_method_to_mock['MethodName']) + "Return = \"\";"

                for component_method_to_mock in component_methods_to_mock:
                    if component['ComponentName'] == component_method_to_mock['ComponentName']:
                        unit_test += "\n\t\t\t" + str(component['ComponentName']) + "Mock." + str(component_method_to_mock['MethodName']) + "(" + ','.join(["\"{any}\"" for a in range(0,component_method_to_mock['NumberOfArgs'])]) + ").returns(" + str(component_method_to_mock['MethodName']) + "Return);"

                unit_test += "\n\t\t\tinjectProperty(Obj, \"" + str(component['ComponentName']) + "\", " + str(component['ComponentName']) + "Mock, \"" + str(component['Scope'])  + "\");"

            # write actual 
            unit_test += "\n\n\t\t\tvar actual = Obj." + str(method_details['Name'])
            unit_test += "\n\t\t\t(" 
            
            for oindex, argument in enumerate(arguments):
                unit_test += "\n\t\t\t\t" + argument[0] + " = " + get_dummy_value_for_type(argument[1])
                if oindex+1 < len(arguments):
                    unit_test += ","                    

            unit_test += "\n\t\t\t);"
            unit_test += "\n\n\t\t\tAssert(actual eq expected,\"Expected something but got something else\");"
            unit_test += "\n\t\t</cfscript>"
            unit_test += "\n\t</cffunction>"
            shell_unit_tests_collection += unit_test
            unit_tests_total += 1

            


        # #############################
        # COMPLETE UNIT TESTS
        # #############################

        # loop through methods and begin writing unit tests 
        for idx, method in enumerate(all_methods):

            method_details = { 'Name' : '', 'Access' : 'public' }
            method_line_by_line = self.view.split_by_newlines(method)
            method_name_re = re.compile("name\s*\=\s*[\"\']", re.IGNORECASE)
            access_level_re = re.compile("access\s*\=\s*[\"\']", re.IGNORECASE)
            functions_re = re.compile("(?<!response)(?<!result)\.[A-Za-z\d_]+\(", re.IGNORECASE)

            # get the method name and access
            for line in method_line_by_line:                
                if not len(method_details['Name']) and method_name_re.search(self.view.substr(line)):
                    for splitted_item in self.view.substr(line).split():
                        if method_name_re.search(splitted_item):
                            method_details['Name'] = re.sub(">","",str(splitted_item))
                            method_details['Name'] = re.sub("[\'\" ]","",str(method_details['Name']))
                            method_details['Name'] = re.sub("name\=","",str(method_details['Name']))
                        elif access_level_re.search(splitted_item):
                            method_details['Access'] = re.sub(">","",str(splitted_item).lower())
                            method_details['Access'] = re.sub("[\'\" ]","",str(method_details['Access']))
                            method_details['Access'] = re.sub("access\=","",str(method_details['Access']))

            # create missing arg unit test
            
            arguments = get_arguments(method, True)

            for argument in arguments:
                unit_test = ""
                unit_test += "\n\n\t<cffunction name=\"" + str(method_details['Name']) + "_MissingArg_" + argument[0] + "_ReturnsException\" access=\"public\" mxunit:expectedException=\"Coldfusion.runtime.MissingArgumentException\">"
                if str(method_details['Access']) == "private" or str(method_details['Access']) == "package":
                    unit_test += "\n\t\t<cfset makePublic(\"" + str(method_details['Name']) + "\") />"

                unit_test += "\n\t\t<cfset variables.ComponentToBeTested." + str(method_details['Name'])
                unit_test += "\n\t\t(" 
                
                other_arguments = list(arguments)
                other_arguments.remove(argument)

                for oindex, other_arg in enumerate(other_arguments):
                    unit_test += "\n\t\t\t" + other_arg[0] + " = " + get_dummy_value_for_type(other_arg[1])
                    if oindex+1 < len(other_arguments):
                        unit_test += ","                    

                unit_test += "\n\t\t) />"
                unit_test += "\n\t</cffunction>"
                complete_unit_tests_collection += unit_test
                unit_tests_total += 1
        

        # fucking string.format, how does it work?
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
        return_msg += shell_unit_tests_collection
        return_msg += "\n\n\n\t<!--------------------------------------------------------------------------"
        return_msg += "\n\tSection: Complete Unit Tests"
        return_msg += "\n\t--------------------------------------------------------------------------->"
        return_msg += complete_unit_tests_collection
        return_msg += "\n\n\n\t<!--------------------------------------------------------------------------"
        return_msg += "\n\tSection: Private methods"
        return_msg += "\n\t--------------------------------------------------------------------------->"
        return_msg += "\n\n\t<cffunction name=\"__GetComponentToBeTested\" access=\"private\">"
        return_msg += "\n\t\t<cfreturn CreateObject(\"component\",\"path.to.ComponentToBeTested\") />"
        return_msg += "\n\t</cffunction>"
        return_msg += "\n\n</cfcomponent>"
        #send to new file
        w = self.view.window()
        w.run_command("new_file")
        v = w.active_view()
        v.insert(edit, 0, return_msg)
