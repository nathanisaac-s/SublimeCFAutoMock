<cfcomponent output="false" hint="This component holds the user functions">
	<cffunction name = "prefillAndUpload" access = "remote" output = "false" returnformat = "json" returntype = "struct">
		<cfargument name="student_pin" type="any" required="true">
	</cffunction>
</cfcomponent>