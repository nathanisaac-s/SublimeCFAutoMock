SublimeCFReAutoMock
===================

WARNING: I am a vim user, not a Sublime user.

This is a fork of [SublimeCFAutoMock](https://github.com/dwkd/SublimeCFAutoMock). I'm going to preface this by saying
that it is truly abominable to parse a language using only flat regex--especially a tag-based language--and attempt to use those flat regexes to somehow capture and generate macro text from the semantics of a language. That actually requires a parser and/or lexer, like ANTLR, which does not use regexes but recursive grammars (think Chomsky) composed of regexes. You wouldn't use the round end of a ball-peen hammer to frame all the houses in a subdivision--you'd use a nailgun.

But this is just meant as a hack for limited use-cases. It just stubs out tests. Between making tests easier to write with a hack and actually using the formally-correct and appropriate tool, I'd prefer that my coworkers had an easier time writing tests: omelets and broken eggs, etc. Regardless, the road to perdition--too easily taken by the naive and the impatient--usually lacks warning signs, but this particular route has one.

This plugin stubs out tests for CFtag functions in CFML classes. We had trouble getting the original plugin to work, so I'm doing it the Open Source Way() and forking with no intention of pull requesting my changes.

*Original text:*

A light sublime plugin that automatically creates MXUnit unit tests from a coldfusion component (cftags only - cfscript and fully scripted to come).


Capabilities
============
  1. Create Setup and Teardown methods
  2. Create unit test shells (user has to finish them) with the following:
    1. Instance of ObjectToBeTested
    2. Mocked components from the variables scope and all their respective methods.
    3. Call to MethodToBeTested from ObjectToBeTested
    4. Dummy assertion call
  3. Create "Missing Arguments" unit tests 
  4. Create private method to get ObjectToBeTested


Install
=======
  CFAutoMock can now be installed via Package Control https://sublime.wbond.net/installation<br>
  Sublime > Preferences > Package Control > Install Package > Type CFAutoMock > Install > Enjoy!
  
Hwo to use
==========
  Open a CFC in Sublime 2 and press CTRL + K (win,linux) or Super + K (mac)
