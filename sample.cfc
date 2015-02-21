<cfcomponent output="false" hint="This component holds the user functions">
	<cffunction name="prefillAndUpload" access = "remote" output = "false" returnformat = "json" returntype = "struct">
		<cfargument name="student_pin" type="any" required="true">
	</cffunction>
</cfcomponent>

<cfcomponent output="false" hint="This component holds the user functions">
	<cffunction name="myOtherAwesomeFunction" access = "remote" output = "false" returnformat = "json" returntype = "struct">
		<cfargument name="student_pin" type="any" required="false">
	</cffunction>
</cfcomponent>

<cfcomponent output="false" hint="This component holds the user functions">
	<cffunction name="evenMoarFunctions" access = "remote" output = "false" returnformat = "json" returntype = "struct">
		<cfargument name="student_pin" type="any" required="false">
		<cfargument name="student_name" type="any" required="false">
	</cffunction>
</cfcomponent>

<cfcomponent output="false" hint="This component holds the user functions">
	<cffunction name="anotherAwesomeFunction" access = "remote" output = "false" returnformat = "json" returntype = "struct">
		<cfargument name="student_name" type="any" required="false">
		<cfargument name="student_address" type="any" required = "true">
	</cffunction>
</cfcomponent>
