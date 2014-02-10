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

"""
Orthography module describes an Orthography class that represents the
orthography of a given language.

OrthographyTranslator facilitates conversion of text in orthography A into
orthography B; takes two Orthography objects at initialization.

This module is adapted and generalized from one written by Patrick Littell
for the conversion of Kwak'wala strings between its many orthographies.

"""

import re

def removeAllWhiteSpace(string):
    """Remove all spaces, newlines and tabs."""
    string = string.replace('\n', '')
    string = string.replace('\t', '')
    string = string.replace(' ', '') 
    return string

def str2bool(string):
    if string == '1':
        return True
    elif string == '0':
        return False
    else:
        return string



class Orthography:
    """The Orthography class represents an orthography used to transcribe a
    language.
    
    Required as input is a comma-delimited string of graphs.  Graphs are
    represented by strings of one or more unicode characters.  Order of graphs
    is important for sorting words or Forms of the language under study.
    
    Graph variants (allographs?) should be grouped together with brackets.
    
    E.g., orthographyAsString = u'[a,a\u0301],b,c,d'
    
    The above orthography string represents an orthography where u'a' and
    u'a\u0301' are both ranked first, u'b' second, u'c' third, etc.
    
    Idiosyncratic arguments are in **kwargs, e.g.,:
     - lowercase: whether or not the orthography is all-lowercase
     - initialGlottalStops: whether it represents glottal stops (assumed to be
       u'7' in the input orthography) word initially.
       
    """
    # Kwakwala to do: 
    # orthographies also differ as to whether stress 
    # is indicated on monosyllabic words:
    #  - NAPA: yes, 
    #  - Grubb: no 
    #  - U'mista: no stress
    #  - SD72: I don't recall

    def __init__(self, orthographyAsString, **kwargs):
        """Get core attributes; primarily, the orthography in various datatypes.
        """
        self.orthographyAsString = removeAllWhiteSpace(orthographyAsString)
        self.orthographyAsList = self.getOrthographyAsList(
            self.orthographyAsString)
        self.orthographyAsDict = self.getOrthographyAsDict(
            self.orthographyAsString)
        self.lowercase = self.getKwargsArg(kwargs, 'lowercase', True)
        self.initialGlottalStops = self.getKwargsArg(kwargs,
                                                    'initialGlottalStops', True)

    def print_(self):
        print 'Orthography Object\n\t%s: %s\n\t%s: %s\n\n%s\n\n%s\n\n%s\n\n' % (
            '# graph types',
            len(self.orthographyAsList),
            '# graphs',
            len(self.orthographyAsDict),
            self.orthographyAsString,
            str(self.orthographyAsList),
            str(self.orthographyAsDict)
        )
        
    def getOrthographyAsList(self, orthography):
        """Returns orthography as a list of lists.

        E.g.,   u'[a,a\u0301],b,c,d'    becomes
                [[u'a',u'a\u0301'],[u'b'],[u'c'],[u'd']]

        """

        inBrackets = False
        result = u''
        for char in orthography:
            if char == u'[':
                inBrackets = True
                char = u''
            elif char == u']':
                inBrackets = False
                char = u''
            if inBrackets and char == u',':
                result += u'|'
            else:
                result += char
        temp = result.split(',')
        result = [item.split('|') for item in temp]
        return result

    def getOrthographyAsDict(self, orthography):
        """Returns orthography as a dictionary of graphs to ranks.
        
        E.g.,   u'[a,a\u0301],b,c,d'    becomes
                {u'a': 0, u'a\u0301': 0, u'b': 1, u'c': 2, u'd': 3}

        """

        inBrackets = False
        result = u''
        for char in orthography:
            if char == u'[':
                inBrackets = True
                char = u''
            elif char == u']':
                inBrackets = False
                char = u''
            if inBrackets and char == u',':
                result += u'|'
            else:
                result += char
        temp = result.split(',')
        result = {}
        for string in temp:
            for x in string.split('|'):
                result[x] = temp.index(string)
        return result

    def getKwargsArg(self, kwargs, key, default=None):
        """Return **kwargs[key] as a boolean, else return default."""
        if key in kwargs:
            return str2bool(kwargs[key])
        else:
            return default


class OrthographyTranslator:
    """Takes two Orthography instances and generates a translate method
    for converting strings form the first orthography to the second.
    """
    def __init__(self, inputOrthography, outputOrthography):
        self.inputOrthography = inputOrthography
        self.outputOrthography = outputOrthography

        # If input and output orthography objects are incompatible for
        #  translation, raise an OrthographyCompatibilityError.
        
        if [len(x) for x in self.inputOrthography.orthographyAsList] != \
            [len(x) for x in self.outputOrthography.orthographyAsList]:
            raise OrthographyCompatibilityError()

        self.prepareRegexes()

    def print_(self):
        for key in self.replacements:
            print '%s\t%s' % (key, self.replacements[key])
            
    def getReplacements(self):
        """Create a dictionary with a key for each graph in the input
        orthography; each such key has as value a graph in the output orthography.

        Note: the input orthography may have more than one correspondent in the
        output orthography.  If this is the case, the default is for the system
        to use the first correspondent and ignore all subsequent ones.  This
        means that the order of graphs entered by the user on the Settings page
        may have unintended consequences for translation...
        """

        replacements = {}
        for i in range(len(self.inputOrthography.orthographyAsList)):
            graphTypeList = self.inputOrthography.orthographyAsList[i]
            for j in range(len(graphTypeList)):
                if graphTypeList[j] not in replacements:
                    replacements[graphTypeList[j]] = \
                        self.outputOrthography.orthographyAsList[i][j]
        self.replacements = replacements

    def makeReplacementsCaseSensitive(self):
        """Update replacements to contain (programmatically) capitalized inputs
        and outputs.
        
        """

        newReplacements = {}
        for key in self.replacements:
            if not self.isCapital(key):
                capital = self.capitalize(key)
                if capital and capital not in self.replacements:
                    # if output orthography is lc, map uc input orthography
                    #  graphs to lc outputs, otherwise to uc outputs
                    if self.outputOrthography.lowercase:
                        newReplacements[capital] = self.replacements[key]
                    else:
                        newReplacements[capital] = \
                            self.capitalize(self.replacements[key])
        self.replacements.update(newReplacements)

    def prepareRegexes(self):
        """Generate the regular expressions for doing character substitutions
        on the input string that will convert it into the output orthography.
        
        """
        
        # build a dictionary representing the mapping between input and output
        #  orthographies
        
        self.getReplacements()
        
        # 4 Possibilities for .lowercase attribute:
        #  1. io.lc = True, oo.lc = True: do nothing (Default)
        #  2. io.lc = True, oo.lc = False: do nothing (I guess we could
        #   capitalize the first word of sentences, but I'm not gonna right now ...)
        #  3. io.lc = False, oo.lc = True: map lc to lc and uc to lc
        #  4. io.lc = False, oo.lc = False: map lc to lc and uc to uc
        
        if not self.inputOrthography.lowercase:
            self.makeReplacementsCaseSensitive()
        
        # Sort the keys according to length, longest words first, to prevent
        #  parts of n-graphs from being found-n-replaced before the n-graph is.
        
        self.replacementKeys = self.replacements.keys()
        self.replacementKeys.sort(lambda x,y:len(y)-len(x))
        
        # This is the pattern that does most of the work
        #  It matches a string in metalanguage tags ("<ml>" and "</ml>") or
        #  a key from self.replacements
        
        self.regex = re.compile(
            "<ml>.*?</ml>|(" + "|".join(self.replacementKeys) + ")"
        )
        
        # If the output orthography doesn't represent initial glottal stops,
        #  but the input orthography does, compile a regex to remove them from
        #  the input orthography.  That way, the replacement operation won't
        #  create initial glottal stops in the output (Glottal stops are assumed
        #  to be represented by "7".)
        
        if self.inputOrthography.initialGlottalStops and \
            not self.outputOrthography.initialGlottalStops:
            self.initialGlottalStopRemover = re.compile("""( |^|(^| )'|")7""")
    
    # This and the constructor will be the only functions other modules will
    #  need to use;
    #  given a string in the input orthography,
    #  returns the string in the output orthography.
    
    def translate(self, text):
        """Takes text as input and returns it in the output orthography."""
        if self.inputOrthography.lowercase:
            text = self.makeLowercase(text)
        if self.inputOrthography.initialGlottalStops and \
            not self.outputOrthography.initialGlottalStops:
            text = self.initialGlottalStopRemover.sub("\\1", text)
        return self.regex.sub(lambda x:self.getReplacement(x.group()), text)

    # We can't just replace each match from self.regex with its value in
    #  self.replacements, because some matches are metalangauge strings that
    #  should not be altered (except to remove the <ml> tags...)
    
    def getReplacement(self, string):
        """If string DOES NOT begin with "<ml>" and end with "</ml>", then treat
        it as an object language input orthography graph and return
        self.replacements[string].
        
        If string DOES begin with "<ml>" and end with "</ml>", then treat it as 
        a metalanguage string and return it with the "<ml>" and "</ml>" tags.
        """
        if string[:4] == '<ml>' and string[-5:] == '</ml>':
            return string
        else:
            #return self.replacements[string]
            return self.replacements.get(string, string)

    # The built-in methods lower(), upper(), isupper(), capitalize(), etc.
    #  don't do exactly what we need here

    def makeLowercase(self, string):
        """Return the string in lowercase except for the substrings enclosed
        in metalanguage tags."""
        patt = re.compile("<ml>.*?</ml>|.")
        def getReplacement(string):
            if string[:4] == '<ml>' and string[-5:] == '</ml>':
                return string
            else:
                return string.lower()
        return patt.sub(lambda x:getReplacement(x.group()), string)

    def capitalize(self, str):
        """If str contains an alpha character, return str with first alpha
        capitalized; else, return empty string.
        """
        result = ""
        for i in range(len(str)):
            if str[i].isalpha(): return str[:i] + str[i:].capitalize()
        return result

    def isCapital(self, str):
        """Returns true only if first alpha character found is uppercase."""
        for char in str:
            if char.isalpha():
                return char.isupper()
        return False


class OrthographyCompatibilityError(Exception):
    pass


class CustomSorter():
    """Takes an Orthography instance and generates a method for sorting a list
    of Forms according to the order of graphs in the orthography.
    
    """

    def __init__(self, orthography):
        self.orthography = orthography
        
    def removeWhiteSpace(self, word):
        return word.replace(' ', '').lower()

    def getIntegerTuple(self, word):
        """Takes a word and returns a tuple of integers representing the rank of
        each graph in the word.  A list of such tuples can then be quickly
        sorted by a Pythonic list's sort() method.
        
        Since graphs are not necessarily Python characters, we have to replace
        each graph with its rank, starting with the longest graphs first.
        """
        
        graphs = self.orthography.orthographyAsDict.keys()
        graphs.sort(key=len)
        graphs.reverse()
         
        for graph in graphs: 
            word = unicode(word.replace(graph,
                            '%s,' % self.orthography.orthographyAsDict[graph]))

        # Filter out anything that is not a digit or a comma
        word = filter(lambda x: x in '01234546789,', word)
        
        return tuple([int(x) for x in word[:-1].split(',') if x])

    def sort(self, forms):
        """Take a list of OLD Forms and return it sorted according to the order
        of graphs in CustomSorter().orthography.
        """
        temp = [(self.getIntegerTuple(self.removeWhiteSpace(form.transcription)),
                 form) for form in forms]
        temp.sort()
        return [x[1] for x in temp]
        
        
if __name__ == '__main__':
    
    # Orthographies as strings
    #  these are the Kwak'wala orthographies used for testing and debugging.
    
    # Orthographies as strings - UNORDERED
    
    kwoldOrthographyString_unordered = u"""
        p,t,tl,c,k,kw,q,qw,7,
        p',t',t'l,c',k',k'w,q',q'w,
        b,d,dl,dz,g,gw,_g,_gw,
        lh,s,x,xw,_x,_xw,h,
        m,n,l,y,w,
        m',n',l',y',w',
        a,e,i,o,u,_a,_e,
        a',e',i',o',u',_a',_e',
        a`,e`,i`,o`,u`,_a`,_e`
        """
    
    napaOrthoghraphyString_unordered = u"""
        p,t,ƛ,c,k,kʷ,q,qʷ,ʔ,
        p̓,t̓,ƛ̓,c̓,k̓,k̓ʷ,q̓,q̓ʷ,
        b,d,λ,d<sup>z</sup>,g,gʷ,ɢ,ɢʷ,
        ɬ,s,x,xʷ,χ,χʷ,h,
        m,n,l,y,w,
        m̓,n̓,l̓,y̓,w̓,
        a,e,i,o,u,ə,ɛ,
        á,é,í,ó,ú,ə́,ɛ́,
        à,è,ì,ò,ù,ə̀,ɛ̀
        """
    
    sd72OrthographyString_unordered = u"""
        p,t,ƛ,c,k,kʷ,q,qʷ,ˀ,
        p̓,t̓,ƛ̓,c̓,k̓,k̓ʷ,q̓,q̓ʷ,
        b,d,λ,d<sup>z</sup>,g,gʷ,ǧ,ǧʷ,
        ł,s,x,xʷ,x̌,x̌ʷ,h,
        m,n,l,y,w,
        m̓,n̓,l̓,y̓,w̓,
        a,e,i,o,u,ə,ɛ,
        á,é,í,ó,ú,ə́,ɛ́,
        a,e,i,o,u,ə,ɛ
        """
    
    umistaOrthographyString_unordered = u"""
        p,t,tł,ts,k,kw,k̲,k̲w,',
        p̓,t̓,t̓ł,t̓s,k̓,k̓w,k̲̓,k̲̓w,
        b,d,dł,d<sup>z</sup>,g,gw,g̲,g̲w,
        ł,s,x,xw,x̲,x̲w,h,
        m,n,l,y,w,
        'm,'n,'l,'y,'w,
        a,e,i,o,u,a̲,e,
        a,e,i,o,u,a̲,e,
        a,e,i,o,u,a̲,e
        """
    
    grubbOrthographyString_unordered = u"""
        p,t,tl,c,ts,k,kw,k̲,k̲w,7,
        p',t',tl',ts',k̓,kw',q',k̲w',
        b,d,dl,dz,g,gw,g̲,g̲w,
        ł,s,x,xw,x̲,x̲w,h,
        m,n,l,y,w,
        m̓,n̓,l̓,y̓,w̓,
        a,eh,i,o,u,e,eh,
        á,éh,í,ó,ú,é,éh,
        a,eh,i,o,u,e,eh
        """
    
    # Orthographies as strings - ORDERED
    
    kwoldOrthographyString = u"""
        [a,a',a`],b,c,c',d,dl,dz,[e,e',e`],[_e,_e',_e`],[_a,_a',_a`],g,gw,_g,_gw,h,[i,i',i`],k,k',kw,k'w,l,l',lh,tl,t'l,m,m',n,n',[o,o',o`],p,p',q,q',qw,q'w,s,t,t',[u,u',u`],w,w',x,xw,_x,_xw,y,y',7
        """
    
    napaOrthographyString = u"""
        [a,á,à],b,c,c̓,d,λ,d<sup>z</sup>,[e,é,è],[ɛ,ɛ́,ɛ̀],[ə,ə́,ə̀],g,gʷ,ɢ,ɢʷ,h,[i,í,ì],k,k̓,kʷ,k̓ʷ,l,l̓,ɬ,ƛ,ƛ̓,m,m̓,n,n̓,[o,ó,ò],p,p̓,q,q̓,qʷ,q̓ʷ,s,t,t̓,[u,ú,ù],w,w̓,x,xʷ,χ,χʷ,y,y̓,ʔ
        """
    
    sd72OrthographyString = u"""
        [a,á,a],b,c,c̓,d,λ,d<sup>z</sup>,[e,é,e],[ɛ,ɛ́,ɛ],[ə,ə́,ə],g,gʷ,ǧ,ǧʷ,h,[i,í,i],k,k̓,kʷ,k̓ʷ,l,l̓,ł,ƛ,ƛ̓,m,m̓,n,n̓,[o,ó,o],p,p̓,q,q̓,qʷ,q̓ʷ,s,t,t̓,[u,ú,u],w,w̓,x,xʷ,x̌,x̌ʷ,y,y̓,ˀ
        """
    
    umistaOrthographyString = u"""
        [a,a,a],b,ts,t̓s,d,dł,d<sup>z</sup>,[e,e,e],[e,e,e],[a,a,a],g,gw,g̲,g̲w,h,[i,i,i],k,k̓,kw,k̓w,l,'l,ł,tł,t̓ł,m,'m,n,'n,[o,o,o],p,p̓,k̲,k̲̓,k̲w,k̲̓w,s,t,t̓,[u,u,u],w,'w,x,xw,x̲,x̲w,y,'y,'
        """
    
    grubbOrthographyString = u"""
        [a,á,a],b,ts,ts',d,dl,dz,[eh,éh,eh],[eh,éh,eh],[e,é,e],g,gw,g̲,g̲w,h,[i,í,i],k,k̓,kw,kw',l,l̓,ł,tl,tl',m,m̓,n,n̓,[o,ó,o],p,p',k̲,q',k̲w,k̲w',s,t,t',[u,ú,u],w,w̓,x,xʷ,x̲,x̲w,y,y̓,7
        """
    
    ooldOrthographyString = u"""[a,á],c,c̓,[ə,ə́],ɣ,h,[i,í],k,k̓,kʷ,k̓ʷ,l,ɬ,ƛ̓,m,m̓,n,n̓,p,p̓,q,q̓,qʷ,q̓ʷ,r,s,t,t̓,[u,ú],w,w̓,x,xʷ,x̌,x̌ʷ,y,y̓,ʕ,ʕ̓,ʔ"""
    
    kutLangGeekCanOrthographyString = u"""
        [a,a·],ȼ,ȼ̓,h,[i,i·],k,k̓,l,ⱡ,m,m̓,n,n̓,p,p̓,q,q̓,s,t,t̓,[u,u·],w,w̓,x,y,y̓,ʔ
        """
    
    kutLangGeekUSOrthographyString = u"""
        [a,a·],ȼ,ȼ̓,h,[i,i·],k,k̓,l,ⱡ,m,m̓,n,n̓,p,p̓,q,q̓,s,t,t̓,[u,u·],w,w̓,x,y,y̓,ʾ
        """
        
    #orthographies["napa"] = Orthography(napaReplacements, True, True)
    #orthographies["sd72"] = Orthography(sd72Replacements, True, True)
    #orthographies["umista"] = Orthography(umistaReplacements, False, False)
    #orthographies["grubb"] = Orthography(grubbReplacements, False, False)
    #orthographies["eng"] = Orthography({}, True, True)

    kwold = Orthography(kwoldOrthographyString)
    napa = Orthography(napaOrthographyString)
    tr = OrthographyTranslator(kwold, napa)
    print tr.translate('tl')
