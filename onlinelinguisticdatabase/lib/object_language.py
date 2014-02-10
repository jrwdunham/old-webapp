#!/usr/local/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2010 Joel Dunham
#
# This file is part of OnlineLinguisticDatabase.
#
# OnlineLinguisticDatabase is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OnlineLinguisticDatabase is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OnlineLinguisticDatabase.  If not, see
# <http://www.gnu.org/licenses/>.

"""This is a module written by Patrick Littell for the conversion of Kwak'wala strings between orthographies.
Originally titled "orthography.py", I (Joel Dunham) have reaned it after the ISO-639-3 code for the language: kwk
"""

import re

class Orthography:

	# The orthography class is constructed with three arguments: A list of replacements from the input orthography to the 
	# output orthography, whether or not the orthography is all-lowercase, and whether it represents glottal stops
	# word initially.
	#
	# To do: If we're being pedantic, the orthographies also differ as to whether stress is indicated on monosyllabic words.
	# NAPA yes, Grubb no, U'mista doesn't show stress anyway, and SD72 I don't recall.

	def __init__(self, replacementList, lowercase=True, initialGlottalStops=True):
		self.replacements = replacementList
		self.lowercase = lowercase
		self.initialGlottalStops = initialGlottalStops
		self.prepareRegexes()

	def prepareRegexes(self):
	
		# If the orthography distinguishes uppercase/lowercase, take a stab at making
		# uppercase characters for each lowercase one entered.  Unless it exists already
	
		if not self.lowercase:
			newReplacements = {}
			for key in self.replacements:
				if not self.isCapital(key):
					capital = self.capitalize(key)
					if capital not in self.replacements:
						newReplacements[capital] = self.capitalize(self.replacements[key])
			self.replacements.update(newReplacements)
		
		# Sort the keys according to length, longest words first, to prevent parts of n-graphs
		# from being found-n-replaced before the n-graph is.
		
		self.replacementKeys = self.replacements.keys()
		self.replacementKeys.sort(lambda x,y:len(y)-len(x))
		
		#for key in self.replacementKeys:
		#	print key + ":" + self.replacements[key]
		#print "--------------"
		
		self.regex = re.compile("(" + "|".join(self.replacementKeys) + ")")
		
		# If the orthography doesn't represent initial glottal stops, compile a regex to remove them.  Merging removal of 
		# glottal stops with the general replacement hasn't been successful and it's not clear to me why.
		
		if not self.initialGlottalStops:
#			self.initialGlottalStopRemover = re.compile("\\b7")	
			self.initialGlottalStopRemover = re.compile("""( |^| '|")7""")	
	
	# This and the constructor will be the only functions other modules will need to use; given a string in the input orthography,
	# gives the output orthography.
		
	def translate(self, text):
		if self.lowercase:
			text = text.lower()
		if not self.initialGlottalStops: 
			text = self.initialGlottalStopRemover.sub("", text)
#		return self.regex.sub(lambda x:self.replacements[x.group()] if x.group() else "", text)
		return self.regex.sub(lambda x:self.replacements[x.group()], text)
		
	# The built-in methods upper(), isupper(), capitalize(), etc. don't do exactly what we need here	
		
	def capitalize(self, str):
		result = ""
		for i in range(len(str)):
			if str[i].isalpha(): return str[:i] + str[i:].capitalize()
		return result

	def isCapital(self, str):
		for char in str:
			if char.isalpha():
				return char.isupper()
		return False

napaReplacements = {
	#u"p"    :		,
	#u"t"    :		,
	u"tl"   : u"ƛ"	,
	#u"c"    :		,
	#u"k"    : 		,
	u"kw"   : u"kʷ"	,
	#u"q"    :		,
	u"qw"   : u"qʷ"	,
	u"7"    : u"ʔ"	,
	
	u"p'"   : u"p̓"	,
	u"t'"   : u"t̓"	,
	u"t'l"  : u"ƛ̓"	,
	u"c'"   : u"c̓"	,
	u"k'"   : u"k̓"	,
	u"k'w"  : u"k̓ʷ"	,
	u"q'"   : u"q̓"	,
	u"q'w"	: u"q̓ʷ"	,	

	#u"b"	:		,
	#u"d"	:		,
	u"dl"	: u"λ"	,
	u"dz"	: u"d<sup>z</sup>"	,
	#u"g"	: 		,
	u"gw"	: u"gʷ"	,
	u"_g"	: u"ɢ"	,
	u"_gw"	: u"ɢʷ"	,

	u"lh"	: u"ɬ"	,
	#u"s"	: 		,
	#u"x"	:		,
	u"xw"	: u"xʷ"	,
	u"_x"	: u"χ"	,
	u"_xw"	: u"χʷ"	,
	#u"h"	:	,
	
	#u"m"	:	,
	#u"n"	:	,
	#u"l"	:	,
	#u"y"	:	,
	#u"w"	:	,
	
	u"m'"	: u"m̓"	,
	u"n'"	: u"n̓"	,
	u"l'"	: u"l̓"	,
	u"y'"	: u"y̓"	,
	u"w'"	: u"w̓"	,	
	
	#u"a"	:		,
	#u"e"	:		,
	#u"i"	:		,
	#u"o"	:		,
	#u"u"	:		,
	u"_a"	: u"ə"	,
	u"_e"	: u"ɛ"	,
	
	u"a'"	: u"á"	,
	u"e'"	: u"é"	,
	u"i'"	: u"í"	,
	u"o'"	: u"ó"	,
	u"u'"	: u"ú"	,
	u"_a'"	: u"ə́"	,	
	u"_e'"	: u"ɛ́"	,
	
	u"a`"	: u"à"	,
	u"e`"	: u"è"	,
	u"i`"	: u"ì"	,
	u"o`"	: u"ò"	,
	u"u`"	: u"ù"	,
	u"_a`"	: u"ə̀"	,
	u"_e`"	: u"ɛ̀"		
}

sd72Replacements = {
	#u"p"    :		,
	#u"t"    :		,
	u"tl"   : u"ƛ"	,
	#u"c"    :		,
	#u"k"    : 		,
	u"kw"   : u"kʷ"	,
	#u"q"    :		,
	u"qw"   : u"qʷ"	,
	u"7"    : u"ˀ"	,
	
	u"p'"   : u"p̓"	,
	u"t'"   : u"t̓"	,
	u"t'l"  : u"ƛ̓"	,
	u"c'"   : u"c̓"	,
	u"k'"   : u"k̓"	,
	u"k'w"  : u"k̓ʷ"	,
	u"q'"   : u"q̓"	,
	u"q'w"	: u"q̓ʷ"	,	

	#u"b"	:		,
	#u"d"	:		,
	u"dl"	: u"λ"	,
	u"dz"	: u"d<sup>z</sup>",
	#u"g"	: 		,
	u"gw"	: u"gʷ"	,
	u"_g"	: u"ǧ"	,
	u"_gw"	: u"ǧʷ"	,

	u"lh"	: u"ł"	,
	#u"s"	: 		,
	#u"x"	:		,
	u"xw"	: u"xʷ"	,
	u"_x"	: u"x̌"	,
	u"_xw"	: u"x̌ʷ"	,
	#u"h"	:		,
	
	#u"m"	:		,
	#u"n"	:		,
	#u"l"	:		,
	#u"y"	:		,
	#u"w"	:		,
	
	u"m'"	: u"m̓"	,
	u"n'"	: u"n̓"	,
	u"l'"	: u"l̓"	,
	u"y'"	: u"y̓"	,
	u"w'"	: u"w̓"	,	
	
	#u"a"	:		,
	#u"e"	:		,
	#u"i"	:		,
	#u"o"	:		,
	#u"u"	:		,
	u"_a"	: u"ə"	,
	u"_e"	: u"ɛ"	,
		
	u"a'"	: u"á"	,
	u"e'"	: u"é"	,
	u"i'"	: u"í"	,
	u"o'"	: u"ó"	,
	u"u'"	: u"ú"	,
	u"_a'"	: u"ə́"	,	
	u"_e'"	: u"ɛ́"	,
	
	u"a`"	: u"a"	,
	u"e`"	: u"e"	,
	u"i`"	: u"i"	,
	u"o`"	: u"o"	,
	u"u`"	: u"u"	,
	u"_a`"	: u"ə"	,
	u"_e`"	: u"ɛ"		
}

umistaReplacements = {
	#u"p"   :		,
	#u"t"   :		,
	u"tl"   : u"tł"	,
	u"c"    : u"ts" ,
	#u"k"   : 		,
	#u"kw"  : 		,
	u"q"    : u"k̲"	,
	u"qw"   : u"k̲w"	,
	u"7"    : u"'"	,
	
	u"p'"   : u"p̓"	,
	u"t'"   : u"t̓"	,
	u"t'l"  : u"t̓ł"	,
	u"c'"   : u"t̓s"	,
	u"k'"   : u"k̓"	,
	u"k'w"  : u"k̓w"	,
	u"q'"   : u"k̲̓"	,
	u"q'w"	: u"k̲̓w"	,	

	#u"b"	:		,
	#u"d"	:		,
	u"dl"	: u"dł"	,
	#u"dz"	: 		,
	#u"g"	: 		,
	#u"gw"	: 		,
	u"_g"	: u"g̲"	,
	u"_gw"	: u"g̲w"	,

	u"lh"	: u"ł"	,
	#u"s"	: 		,
	#u"x"	:		,
	#u"xw"	: 		,
	u"_x"	: u"x̲"	,
	u"_xw"	: u"x̲w"	,
	#u"h"	:		,
	
	#u"m"	:		,
	#u"n"	:		,
	#u"l"	:		,
	#u"y"	:		,
	#u"w"	:		,
	
	u"m'"	: u"'m"	,
	u"n'"	: u"'n"	,
	u"l'"	: u"'l"	,
	u"y'"	: u"'y"	,
	u"w'"	: u"'w"	,	
	
	#u"a"	:		,
	#u"e"	:		,
	#u"i"	:		,
	#u"o"	:		,
	#u"u"	:		,
	u"_a"	: u"a̲"	,
	u"_e"	: u"e"	,

	u"a'"	: u"a"	,
	u"e'"	: u"e"	,
	u"i'"	: u"i"	,
	u"o'"	: u"o"	,
	u"u'"	: u"u"	,
	u"_a'"	: u"a̲"	,	
	u"_e'"	: u"e"	,
	
	u"a`"	: u"a"	,
	u"e`"	: u"e"	,
	u"i`"	: u"i"	,
	u"o`"	: u"o"	,
	u"u`"	: u"u"	,
	u"_a`"	: u"a̲"	,
	u"_e`"	: u"e"			
	
}

grubbReplacements = {
	#u"p"   :		,
	#u"t"   :		,
	#u"tl"  : 		,
	u"c"    : u"ts",
	#u"k"   : 		,
	#u"kw"  : 		,
	u"q"    : u"k̲"	,
	u"qw"   : u"k̲w"	,
	#u"7"    : 	,
	
	#u"p'"   :		,
	#u"t'"   :		,
	u"t'l"  : u"tl'",
	u"c'"   : u"ts'",
	#u"k'"   : u"k̓"	,
	u"k'w"  : u"kw'",
	#u"q'"   : 		,
	u"q'w"	: u"k̲w'",	

	#u"b"	:		,
	#u"d"	:		,
	u"dl"	: u"dl"	,
	#u"dz"	: 		,
	#u"g"	: 		,
	#u"gw"	: 		,
	u"_g"	: u"g̲"	,
	u"_gw"	: u"g̲w"	,

	u"lh"	: u"ł"	,
	#u"s"	: 		,
	#u"x"	:		,
	#u"xw"	: 		,
	u"_x"	: u"x̲"	,
	u"_xw"	: u"x̲w"	,
	#u"h"	:		,
	
	#u"m"	:		,
	#u"n"	:		,
	#u"l"	:		,
	#u"y"	:		,
	#u"w"	:		,
	
	u"m'"	: u"m̓"	,
	u"n'"	: u"n̓"	,
	u"l'"	: u"l̓"	,
	u"y'"	: u"y̓"	,
	u"w'"	: u"w̓"	,	
	
	#u"a"	:		,
	u"e"	: u"eh"	,
	#u"i"	:		,
	#u"o"	:		,
	#u"u"	:		,
	u"_a"	: u"e"	,
	u"_e"	: u"eh"	,

	u"a'"	: u"á"	,
	u"e'"	: u"éh"	,
	u"i'"	: u"í"	,
	u"o'"	: u"ó"	,
	u"u'"	: u"ú"	,
	u"_a'"	: u"é"	,	
	u"_e'"	: u"éh"	,
	
	u"a`"	: u"a"	,
	u"e`"	: u"eh"	,
	u"i`"	: u"i"	,
	u"o`"	: u"o"	,
	u"u`"	: u"u"	,
	u"_a`"	: u"e"	,
	u"_e`"	: u"eh"		
		
}


orthographies = {}

orthographies["napa"] = Orthography(napaReplacements, True, True)
orthographies["sd72"] = Orthography(sd72Replacements, True, True)
orthographies["umista"] = Orthography(umistaReplacements, False, False)
orthographies["grubb"] = Orthography(grubbReplacements, False, False)
orthographies["eng"] = Orthography({}, True, True)

def getInstance(lang):
	return orthographies[lang]





