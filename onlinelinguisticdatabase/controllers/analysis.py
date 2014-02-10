# −*− coding: UTF−8 −*−

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

import logging
import subprocess
import os
import codecs
import re
import pickle
import urllib
import string

from datetime import datetime
from random import shuffle


try:
    import json
except ImportError:
    import simplejson as json

from pylons import config, request, response, session, app_globals, tmpl_context as c
from pylons.controllers.util import abort, redirect_to
from pylons.decorators.rest import restrict

from form import SearchFormForm
from onlinelinguisticdatabase.lib.base import BaseController, render
from onlinelinguisticdatabase.lib.analysisObjects import Phonology
import onlinelinguisticdatabase.lib.helpers as h
from onlinelinguisticdatabase.lib.myworker import worker_q
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta

from sqlalchemy.sql import not_

log = logging.getLogger(__name__)


delim = app_globals.morphDelimiters
phonologyFileName = u'phonology.foma'
phonologyRegexFileName = u'phonology_regex.foma'
phonologyBinaryFileName = u'phonology.foma.bin'
compilePhonologyFileName = u'compilephonology.sh'
saveStackPhonologyFileName = u'savestackphonology.sh'
morphotacticsFileName = u'morphotactics.foma'
morphophonologyFileName = u'morphophonology.foma'
morphophonologyBinaryFileName = u'morphophonology.foma.bin'
compileMorphophonologyFileName = u'compilemorphophonology.sh'
probabilityCalculatorFileName = u'probabilityCalculator.pickle'
lexiconFileName = u'lexicon.txt'
analyzedWordsFileName = u'analyzed_words.txt'
orthographicVariationFileName = u'orthographicvariation.foma'
orthographicVariationBinaryFileName = u'orthographicvariation.foma.bin'
analysisDataDir = config['app_conf']['analysis_data']

def whereis(program):
    log.debug('Here is the request environ: %s' % request.environ.get('PATH', ''))
    log.debug('Here is the os environ: %s' % os.environ.get('PATH', ''))
    for path in request.environ.get('PATH', '').split(':'):
        if os.path.exists(os.path.join(path, program)) and \
            not os.path.isdir(os.path.join(path, program)):
            return os.path.join(path, program)
    return None



def prod(l):
    return reduce(lambda x, y: x * y, l)


def checkRequirements():
    
    try:
        parserFiles = os.listdir(analysisDataDir)
    except OSError:
        parserFiles = []
    c.phonologyExists = phonologyFileName in parserFiles
    c.morphotacticsExists = morphotacticsFileName in parserFiles
    c.morphophonologyExists = morphophonologyFileName in parserFiles
    c.morphophonologyBinaryExists = morphophonologyBinaryFileName in parserFiles
    c.probabilityCalculatorExists = probabilityCalculatorFileName in parserFiles

    c.fomaIsInstalled = whereis('foma')
    c.flookupIsInstalled = whereis('flookup')


def generateBinaryFomaFSTFile():

    fstSourceFileName = 'phonology.foma'
    fstSourceFilePath = os.path.join(analysisDataDir, fstSourceFileName)

    fstBinaryFileName = 'phon_bin.foma'
    fstBinaryFilePath = os.path.join(analysisDataDir, fstBinaryFileName)

    process = subprocess.Popen(
        ['foma'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    msg = 'source %s\nsave stack %s\n' % (fstSourceFilePath, fstBinaryFilePath)
    result = process.communicate(msg)[0]


def getParsesFromFoma(word):
    """Use flookup and the morphophonology FST to get a list of possible parses
    for the word.

    """

    word = u'#%s#' % word
    morphophonologyBinaryFilePath = os.path.join(
        analysisDataDir, morphophonologyBinaryFileName)

    process = subprocess.Popen(
        ['flookup', '-x', morphophonologyBinaryFilePath],
        shell=False,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE)
    process.stdin.write(word.encode('utf-8'))
    result = unicode(process.communicate()[0], 'utf-8').split('\n')
    return [x[1:-1] for x in result if x]


def getOrthographicVariants(word, limit=20):
    """Use flookup and the orthographicvariation FST to get possible alternate
    spellings/transcriptions of the word.  Return these ranked by their minimum
    edit distance from the word.

    """

    print '\n\n\nTRYING TO GET VARIANTS FOR: %s\n\n\n' % word

    # Check to see if we have the orthographic variation FST file
    if orthographicVariationBinaryFileName not in os.listdir(analysisDataDir):
        return []

    # Check to see if the nltk module is installed
    try:
        from nltk.metrics import edit_distance
    except ImportError:
        return []

    # Get variants from flookup
    word = u'#%s#' % word
    orthographicVariationBinaryFilePath = os.path.join(
        analysisDataDir, orthographicVariationBinaryFileName)
    process = subprocess.Popen(
        ['flookup', '-x', '-i', orthographicVariationBinaryFilePath],
        shell=False,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE)
    process.stdin.write(word.encode('utf-8'))
    result = unicode(process.communicate()[0], 'utf-8').split('\n')
    #print 'Number of results from flookup: %d' % len(result)

    # Remove results that are too long or too short
    margin = 2
    if len(result) > 1000:
        margin = 1
    result = [x for x in result
              if len(x) < len(word) + 2 and len(x) > len(word) -2]
    #print 'Number of results needing edit distancing: %d' % len(result)

    # Sort variants by minimum edit distance
    result = [(x, edit_distance(word, x)) for x in result]
    result.sort(key=lambda x: x[1])

    # Take only the top <limit> # of results
    result = result[:limit]

    # Remove the first result if it has a MED of 0
    if result[0][1] == 0:
        result = result[1:]
    result = [x[0][1:-1] for x in result if x] # Remove hash symbols
    return result


def applyFomaPhonology(i, dir):
    i = u'#%s#' % i
    phonologyBinaryFilePath = os.path.join(
        analysisDataDir, phonologyBinaryFileName)

    cmdList = ['flookup', '-x', phonologyBinaryFilePath]
    if dir == 'inverse':
        cmdList = ['flookup', '-x', '-i', phonologyBinaryFilePath]
    process = subprocess.Popen(
        cmdList,
        shell=False,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE)
    process.stdin.write(i.encode('utf-8'))
    result = unicode(process.communicate()[0], 'utf-8').split('\n')
    return [x[1:-1] for x in result if x]


def getFormsWithAnalyzedWords():
    """Get all Forms with non-empty mb, mg and scs fields such that all of
    these fields, as well as the tr field, have the same number of "words".

    """

    forms = meta.Session.query(model.Form).filter(
        model.Form.morphemeBreak != u'').filter(
        model.Form.morphemeGloss != u'').filter(
        model.Form.syntacticCategoryString != u'').all()

    # Get all forms whose mb, mg and scs fields have an equal number of
    #  words
    forms = [form for form in forms if
             len(form.transcription.split()) ==
             len(form.morphemeBreak.split()) ==
             len(form.morphemeGloss.split()) ==
             len(form.syntacticCategoryString.split())]

    return forms


def getAnalyzedWords(forms, lexCats, delim):
    """Return all of the analyzed word tokens present in forms.  The criteria
    for an analyzed word is that it be analyzed as containing only morphemes
    whose categories are from the set of lexical categories given in lexCats.

    """

    def isAGoodAnalyzedWord(word):
        catList = re.split('|'.join(delim), word[3])
        return not set(catList) - set(lexCats)

    result = []
    for f in forms:
        tr = f.transcription.split()
        mb = f.morphemeBreak.split()
        mg = f.morphemeGloss.split()
        sc = f.syntacticCategoryString.split()
        words = [x for x in zip(tr, mb, mg, sc) if isAGoodAnalyzedWord(x)]
        result += words
    return result


def getAllSyncatWordStrings(delim):
    """Returns the set of all syntactic category word strings in the
    database.  E.g., ['Agr-N', 'Agr-V', ...].

    """

    def syncatStringIsGood(syncatString, delim):
        # Filters out syntactic category strings containing the category'?'
        return '?' not in re.split('|'.join(delim), syncatString)

    forms = getFormsWithAnalyzedWords()

    syncatStrings = [form.syntacticCategoryString for form in forms]

    syncatStringWords = {}
    for s in syncatStrings:
        for sw in s.split():
            if syncatStringIsGood(sw, delim):
                syncatStringWords[sw] = 0

    return syncatStringWords.keys()


def getLexicalItems(delim):
    """Returns the set of Forms in the database that represent lexical
    items.  The system assumes lexical items to be those that lack
    's', 'S', 'sentence', 'sent' or 'Sentence' as their syntactic
    category AND lack spaces in their transcription fields.

    """

    def isAValidLexicalItem(f):
        nonLexicalCategories = ['s', 'S', 'sentence', 'sent' or 'Sentence']
        delimiters = re.compile(u'|'.join(delim))
        if f.syntacticCategory and \
            (f.syntacticCategory.name not in nonLexicalCategories) and \
            not delimiters.search(f.morphemeGloss):
            return True
        else:
            return False

    forms = meta.Session.query(model.Form).filter(not_(
        model.Form.transcription.like(u'% %'))).all()
    forms = [f for f in forms if isAValidLexicalItem(f)]

    lexicalItems = {}

    for form in forms:
        t = form.transcription
        key = form.syntacticCategory.name
        if len(key) < 2:
            key = '%sCategory' % key
        if form.morphemeGloss:
            g = form.morphemeGloss.replace(u' ', u'.')
        else:
            g = form.glosses[0].gloss.replace(u' ', u'.')
        f = (t, g)
        try:
            lexicalItems[key].append(f)
        except KeyError:
            lexicalItems[key] = [f]

    return lexicalItems

def getLexicalItemsFromFile(delim):
    """Tries to get the lexical items from the lexicon.txt file.  If that fails,
    it returns the result of getLexicalItems (which gets the lexical items from
    the db.)

    """

    lexiconFilePath = os.path.join(analysisDataDir, lexiconFileName)
    try:
        print 'Getting lexical items from file.'
        lexiconFile = codecs.open(lexiconFilePath, 'r', 'utf-8')
        lexicalItems = {}
        for line in lexiconFile:
            if line[0] == u'#':
                key = line[1:-1]
                lexicalItems[key] = []
            elif line != u'\n':
                value = tuple(line[:-1].split())
                lexicalItems[key].append(value)
        return lexicalItems
    except IOError:
        print 'Getting lexical items from database.'
        return getLexicalItems(delim)


# Foma reserved symbols.  See
#  http://code.google.com/p/foma/wiki/RegularExpressionReference#Reserved_symbols
fomaReserved = [u'\u0021', u'\u0022', u'\u0023', u'\u0024', u'\u0025', u'\u0026',
    u'\u0028', u'\u0029', u'\u002A', u'\u002B', u'\u002C', u'\u002D', u'\u002E',
    u'\u002F', u'\u0030', u'\u003A', u'\u003B', u'\u003C', u'\u003E', u'\u003F',
    u'\u005B', u'\u005C', u'\u005D', u'\u005E', u'\u005F', u'\u0060', u'\u007B',
    u'\u007C', u'\u007D', u'\u007E', u'\u00AC', u'\u00B9', u'\u00D7', u'\u03A3',
    u'\u03B5', u'\u207B', u'\u2081', u'\u2082', u'\u2192', u'\u2194', u'\u2200',
    u'\u2203', u'\u2205', u'\u2208', u'\u2218', u'\u2225', u'\u2227', u'\u2228',
    u'\u2229', u'\u222A', u'\u2264', u'\u2265', u'\u227A', u'\u227B']

def escapeFomaReserved(i):
    def escape(ii):
        if ii in fomaReserved:
            ii = u'%' + ii
        return ii
    return ''.join([escape(x) for x in i])

def getFomaMorphotacticsFile(syncatWordStrings, lexicalItems, delim):
    """Returns a string consisting of a series of foma statements that
    define a morphotactic FST.
    
    Because of some quirks inherent to the foma script parser, long
    define statements need to be broken up into shorter ones and then
    concatenated via disjunction.  Hence the ugly code below.

    """

    patt = re.compile('(%s)' % '|'.join(delim))
    tmp = [patt.sub(' "\\1" ', s) for s in syncatWordStrings]

    fomaMorphotacticsDefinition = {}
    c = 1
    for i in range(len(tmp)):
        word = tmp[i]
        if (i % 100 == 99) or (i == len(tmp) - 1):
            tmp2 += ' | \n(%s);' % word
            fomaMorphotacticsDefinition[varName] = tmp2
        elif i % 100 == 0:
            varName = u'morphotactics%d' % c
            tmp2 = '(%s)' % word
            c += 1
        else:
            tmp2 += ' | \n(%s)' % word

    if len(fomaMorphotacticsDefinition) > 1:
        subs = []
        subNames = fomaMorphotacticsDefinition.keys()
        for k in fomaMorphotacticsDefinition:
            definition = 'define %s %s' % (k,
                fomaMorphotacticsDefinition[k])
            subs.append(definition)
        fomaMorphotacticsDefinition = u'\n\n'.join(subs) + \
            u'\n\ndefine morphotactics "#" (%s) "#";' % ' | \n'.join(subNames)

    else:
        fomaMorphotacticsDefinition = u'define morphotactics "#" (%s) "#"' % (
            fomaMorphotacticsDefinition.values()[0])

    def getLexicalItemDefinition(label, forms):

        def regexify(i):
            """Returns the string formatted for a foma regular expression.  That
            is, characters separated by a space and reserved characters escaped.

            """

            #return ' '.join(['"%s"' % z for z in i])
            return escapeFomaReserved(' '.join(list(i)))

        if len(forms) < 100:
            
            return u'define %s [%s];\n\n' % (label,
                '|\n    '.join(
                    [regexify(x[0]) + '"|%s":0' % x[1] for x in forms]))
        else:
            lexicalItemDefinition = {}
            c = 1
            tmp = u''
            for i in range(len(forms)):
                form = forms[i]
                if (i % 100 == 99) or (i == len(forms) - 1):
                    tmp += '|\n    %s"|%s":0];' % (regexify(form[0]), form[1])
                    lexicalItemDefinition[varName] = tmp
                elif i % 100 == 0:
                    varName = u'%s%d' % (label, c)
                    tmp = '[%s"|%s":0' % (regexify(form[0]), form[1])
                    c += 1
                else:
                    tmp += '|\n    %s"|%s":0' % (regexify(form[0]), form[1])

            subs = []
            subNames = lexicalItemDefinition.keys()
            for k in lexicalItemDefinition:
                definition = 'define %s %s' % (k,
                    lexicalItemDefinition[k])
                subs.append(definition)
            lexicalItemDefinition = u'\n\n'.join(subs) + \
                u'\n\ndefine %s %s;\n\n' % (label, ' | '.join(subNames))
            return lexicalItemDefinition

    fomaLexicalItemsDefinitions = u''
    for li in lexicalItems:
        label = li
        forms = lexicalItems[li]
        fomaLexicalItemsDefinitions += getLexicalItemDefinition(label,
                                                                forms)
    return u'%s\n\n%s' % (fomaLexicalItemsDefinitions,
                     fomaMorphotacticsDefinition)


def getNGramCounts(analyzedWords, lexItms):
    """Returns a tuple (unigrams, bigrams) where each is a dict from a unigram/
    bigram to a count of its occurrences in the database.

    """

    unigrams = {}
    bigrams = {}

    # Increment the value of a key in a dict; if key doesn't exist, assign value 1
    def incrementDict(_dict, key):
        try:
            _dict[key] += 1
        except KeyError:
            _dict[key] = 1

    # Count the unigrams & bigrams from the analyzed words
    for w in analyzedWords:
        mb = re.split(u'|'.join(delim), w[1])
        mg = re.split(u'|'.join(delim), w[2])
        bgMorphemes = zip(mb, mg)
        incrementDict(unigrams, u'<l>')
        incrementDict(unigrams, u'<r>')
        for i in range(len(bgMorphemes)):
            m = bgMorphemes[i]
            m = u'%s|%s' % (m[0], m[1])
            incrementDict(unigrams, m)
            if i == 0:
                incrementDict(bigrams, (u'<l>', m))
            else:
                mPrev = bgMorphemes[i - 1]
                mPrev = u'%s|%s' % (mPrev[0], mPrev[1])
                incrementDict(bigrams, (mPrev, m))
            if i == (len(bgMorphemes) - 1):
                incrementDict(bigrams, (m, u'<r>'))

    # Upate the unigram counts with the lexical items (count = 0)
    for syncat in lexItms:
        liList = lexItms[syncat]
        for li in liList:
            li = '|'.join(li)
            if li not in unigrams:
                unigrams[li] = 0

    return (unigrams, bigrams)


class ProbabilityCalculator(object):

    def __init__(self, unigrams, bigrams, delim):
        self.unigrams = unigrams
        self.bigrams = bigrams
        self.delim = delim
        self.N = len(unigrams)
        self.bigram2probability = {}

    def getBigramsFromAnalysis(self, analysis):
        """Analysis is a string like u'chien|dog-s|PL'.  On this string, this
        function would return

            [(u'<l>', u'chien|dog'), (u'chien|dog', u's|PL'), (u's|PL', u'<r>')]

        """

        tmp = [u'<l>'] + re.split('|'.join(self.delim), analysis) + [u'<r>']
        result = []
        for i in range(len(tmp) - 1):
            result.append((tmp[i], tmp[i + 1]))
        return result

    def getProbOfBigram(self, bigram, analysis=None):
        try:
            result = self.bigram2probability[bigram]
        except KeyError:
            numerator = self.bigrams.get(bigram)
            if numerator:
                numerator += 1
            else:
                numerator = 1
            try:
                denominator = self.unigrams[bigram[0]] + self.N
                probability = numerator / float(denominator)
            except KeyError:
                
                print 'ERROR: could not find count for %s' % bigram[0]
                if analysis:
                    print 'the analysis variable is not None'
                probability = 0.00000000001
            self.bigram2probability[bigram] = probability
            result = probability
        return result

    def getProbability(self, analysis):
        anaBigrams = self.getBigramsFromAnalysis(analysis)
        probs = [self.getProbOfBigram(b, analysis) for b in anaBigrams]
        result = prod(probs)
        return result


def getProbCalc():
    """Try to get a probability calculator object.

    """

    try:
        probCalc = app_globals.wordProbabilityCalculator
    except AttributeError:
        try:
            probabilityCalculatorPath = os.path.join(analysisDataDir,
                                            probabilityCalculatorFileName)
            probCalcPickleFile = open(probabilityCalculatorPath, 'rb')
            probCalc = pickle.load(probCalcPickleFile)
            app_globals.wordProbabilityCalculator = probCalc
        except IOError:
            probCalc = None
    return probCalc


def splitBreakFromGloss(analysis):
    """Take something like 'abc|123-def|456=ghi|789' and return
    ('abc-def=ghi', '123-456=789').

    """

    splitter = re.compile('(%s)' % '|'.join(delim))
    analysis = splitter.split(analysis)
    mb = u''
    mg = u''
    for i in range(len(analysis)):
        try:
            if i % 2 == 0:
                mb += analysis[i].split('|')[0]
                mg += analysis[i].split('|')[1]
            else:
                mb += analysis[i]
                mg += analysis[i]
        except IndexError:
            print 'Warning: unable to split %s, the %d element of %s' % (
                analysis[i], i, str(analysis))
    return (mb, mg)


def getTrainingAndTestSets(analyzedWords):
    mark = int(len(analyzedWords) * 0.9)
    shuffle(analyzedWords)
    return (analyzedWords[:mark], analyzedWords[mark:])


def analyzeAccentation():
    """
        - gets each analyzed word form analyzed_words.txt
        - phonologizes the morpheme break line using phonology.foma (apply down)
        - checks whether the accentation of the phonologized mb matches that of
          the transcription
        - prints a report ('prominence_output.txt') with counts, percentages and
          lists the non-matching cases sorted by syllable count and,
          secondarily, prominence location

    """

    def getProminentSyllables(word):
        """Return a tuple of the form (x, y) where y is the number of syllables
        in word and x is a tuple representing the location of the prominent
        syllables in word.  E.g., x = () means 'no prominences', x = (1,) means
        'prominence on syllable 1 only' and x = (2, 4) means 'prominence on
        syllables 2 and 4.

        """

        word = u'#%s#' % word

        unaccentedVowels = [u'a', u'i', u'o', u'u', u'e', u'A', u'I', u'O', u'U']
        accentedVowels = [u'a\u0301', u'i\u0301', u'o\u0301',
            u'\u00c1', u'\u00ED', u'\u00F2', u'\u00CD', u'\u00D3', u'\u00E1',
            u'\u00F3']
        vowels = unaccentedVowels + accentedVowels

        patt = u'([%s]+)' % u'|'.join(vowels)
        patt = re.compile(patt)
        wordList = patt.split(word)

        prominentIndices = []
        for i in range(len(wordList)):
            syllPart = wordList[i]
            if set(list(syllPart)) & set(accentedVowels):
                prominentIndices.append(i)
        prominentSyllables = tuple([(x / 2) + 1 for x in prominentIndices])

        numSyllables = len(wordList) / 2
        return (prominentSyllables, numSyllables)

    # Get the (unique) analyzed words
    analyzedWordsPath = os.path.join(analysisDataDir, analyzedWordsFileName)
    f = codecs.open(analyzedWordsPath, 'r', 'utf-8')
    lines = f.readlines()
    lines = list(set(lines))

    syllCount2Form = {}
    output = u''
    prominenceIsGood = 0
    prominenceIsBad = 0
    spacer = '#' * 80
    spacer2 = '_' * 80
    spacer3 = '+' * 80
    outputFile = codecs.open(
        os.path.join(analysisDataDir, u'prominence_output.txt'),
        'w', 'utf-8')

    # Get those analyzed words whose prominence pattern is not as expected and
    #  sort them by number of syllables and location of prominence(s).
    i = 1
    for line in lines:
        print '%d/%d' % (i, len(lines))
        i += 1

        line = line.split()
        tr = removeWordFinalPunctuation(line[0])
        prominentSyllables, numSyllables = getProminentSyllables(tr)

        mbPhonologized = applyFomaPhonology(line[1], 'inverse')
        mbPromSyllsNumSylls = [getProminentSyllables(x) for x in mbPhonologized] 
        record = (tr, mbPhonologized, line[1])

        if (prominentSyllables, numSyllables) not in mbPromSyllsNumSylls:
            prominenceIsBad += 1
            try:
                syllCount2Form[numSyllables][prominentSyllables].append(record)
            except KeyError:
                if numSyllables not in syllCount2Form:
                    syllCount2Form[numSyllables] = {prominentSyllables: [record]}
                else:
                    syllCount2Form[numSyllables][prominentSyllables] = [record]
        else:
            prominenceIsGood += 1

    # Write the report of the analysis
    output += u'%s\nProminence Analysis of Blackfoot -- Report\n%s\n\n' % (
        spacer, spacer)
    output += '-%d unique forms analyzed\n' % len(lines)
    output += '-%d (%f) had prominence in the expected location\n' % (
        prominenceIsGood, prominenceIsGood / float(len(lines)))
    output += '-%d (%f) did not have prominence in the expected location\n' % (
        prominenceIsBad, prominenceIsBad / float(len(lines)))
    output += '\nDetails of forms with unexpected prominence location\n%s\n\n' \
              % spacer
    for key in sorted(syllCount2Form.keys()):
        prom2TokDict = syllCount2Form[key]
        output += '\n\n%d-syllable forms (count: %d)\n%s\n' % (
            key, sum([len(x) for x in prom2TokDict.values()]), spacer2)
        for promLoc in sorted(prom2TokDict.keys()):
            recordList = sorted(prom2TokDict[promLoc])
            output += '\n\nForms with prominence at syllable(s) %s\n%s\n' % (
                ', '.join([str(x) for x in promLoc]),
                spacer3)
            for record in recordList:
                output += u'%s\t%s\n' % (record[0], u', '.join(record[1]))
    outputFile.write(output)
    outputFile.close()


def removeWordFinalPunctuation(word):
    punct = ['"', '.', '?', '!', u'\u2019', u'\u201D', u'\u201C',
        u'\u2026', u')', u'(', u'*', u'-', u';', u':', u',']
    if word[-1] in punct:
        word = word[:-1]
    return word


def removeExtraneousPunctuation(word):
    punctuation = string.punctuation.replace(
        "'", "") + u'\u2019\u201D\u201C\u2026'
    patt = re.compile('[%s]' % re.escape(punctuation))
    return patt.sub('', word)


def saveAnalyzedWordsFile(analyzedWords, fname=None):
    if not fname: fname = analyzedWordsFileName
    analyzedWordsFilePath = os.path.join(analysisDataDir, fname)
    analyzedWordsFile = codecs.open(analyzedWordsFilePath, 'w', 'utf-8')
    for w in analyzedWords:
        line = u'%s\n' % u' '.join(w)
        analyzedWordsFile.write(line)
    analyzedWordsFile.close()



class AnalysisController(BaseController):

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def index(self):
        checkRequirements()
        try:
            phonologyFilePath = os.path.join(analysisDataDir, phonologyFileName)
            phonologyFile = codecs.open(phonologyFilePath, 'r', 'utf-8')
            c.phonology = phonologyFile.read()
            phonologyFile.close()
        except IOError:
            c.phonology = u''
        return render('/derived/analysis/index.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def phonology(self):
        """The phonology method simply serves the phonology.html page which
        links to the Javascript public/javascript/phonology.js.
        All "phonology_"-prefixed methods are Ajax responders.

        """

        return render('/derived/analysis/phonology.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def phonology_dependencies_installed(self):
        fomaPath = whereis('foma')
        flookupPath = whereis('flookup')
        log.debug(flookupPath)
        if fomaPath and flookupPath:
            return json.dumps(True)
        return json.dumps(False)

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def phonology_add(self):
        """Performs the following actions:
        
        - saves the phonology metadata to the database (name, description, etc.)
        - creates the directory for this phonology:
          analysis/phonology/phonology_%d
        - writes the foma script file (phonology.foma)
        - writes the shell script to compile the foma script
          (phonologycompile.sh)
        - compiles the phonology script (creates phonology.foma.bin)

        """

        # 1. Get values entered by user (validation done in Javascript)
        log.debug('Getting user inputs.')
        values = urllib.unquote_plus(unicode(request.body, 'utf-8'))
        values = json.loads(values)

        # 2. Create phonology object and write it to database
        log.debug('Writing phonology metadata to database.')
        phonology = model.Phonology()
        now = datetime.utcnow()
        phonology.name = values['name']
        phonology.description = values['description']
        phonology.script = values['script']
        phonology.enterer = meta.Session.query(model.User).get(
            int(session['user_id']))
        phonology.datetimeEntered = now
        phonology.datetimeModified = now
        meta.Session.add(phonology)
        meta.Session.commit()

        # 3. Create directory structure, write foma and foma compile scripts
        phonology.setup()

        # 4. Compile
        phonology.compile() 

        # 5. Return JSON representation
        phonologyInJSON = phonology.getAttributesInJSON()
        return phonologyInJSON

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def phonology_edit(self):
        """Performs the following actions:
        
        - updates the phonology metadata in the database
        - if script is different:
          - writes the new foma script file
          - compiles the phonology script

        """

        # 1. Get values entered by user (validation done in Javascript)
        log.debug('Getting user inputs.')
        values = urllib.unquote_plus(unicode(request.body, 'utf-8'))
        values = json.loads(values)

        phonology = meta.Session.query(model.Phonology).get(int(values['id']))

        if phonology.script != values['script']:
            log.debug('Script needs re-writing and -compiling.')
            # 3. Create directory structure, write foma and foma compile scripts
            phonology.script = values['script']
            phonology.setup()

            # 4. Compile
            phonology.compile() 

        # 2. Create phonology object and write it to database
        log.debug('Updating phonology metadata in database.')
        now = datetime.utcnow()
        phonology.name = values['name']
        phonology.description = values['description']
        phonology.script = values['script']
        phonology.modifier = meta.Session.query(model.User).get(
            int(session['user_id']))
        phonology.datetimeModified = now
        meta.Session.add(phonology)
        meta.Session.commit()

        # 5. Return JSON representation
        phonologyInJSON = phonology.getAttributesInJSON()
        return phonologyInJSON

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def phonology_delete(self):
        """Deletes the phonology with the ID provided in the POST stream.

        """

        log.debug('Getting phonology to delete.')
        id = urllib.unquote_plus(unicode(request.body, 'utf-8'))
        id = json.loads(id)
        phonology = meta.Session.query(model.Phonology).get(id)

        log.debug('Deleting phonology files.')
        filesDeleted = phonology.delete()

        if filesDeleted:
            log.debug('Deleting database entry for phonology.')
            meta.Session.delete(phonology)
            meta.Session.commit()
            return json.dumps(True)
        else:
            log.debug('Unable to delete files; therefore db entry intact.')
            return json.dumps(False)

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def phonology_get(self):
        """Return all of the phonologies.
        
        """

        phonologies = meta.Session.query(model.Phonology).order_by(
            model.Phonology.name)
        return json.dumps([p.getAttributesAsDict() for p in phonologies])

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def phonology_apply_to_token(self):
        log.debug('Phonologizing token provided by user.')
        inputs = urllib.unquote_plus(unicode(request.body, 'utf-8'))
        inputs = json.loads(inputs)
        token = inputs['token'];
        ID = inputs['id']

        phonology = Phonology()
        phonology.setID(ID)
        phonology.getFilePaths()
        surfaceForms = phonology.phonologize(token)
        return json.dumps(surfaceForms)

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def phonology_apply_to_self(self):
        log.debug('Phonologizing #test entries in the script.')
        inputs = urllib.unquote_plus(unicode(request.body, 'utf-8'))
        inputs = json.loads(inputs)
        ID = inputs['id']
        phonology = Phonology()
        phonology.setID(ID)
        phonology.getFilePaths()
        result = phonology.phonologizeInternalTests()
        log.debug('\n'.join([str(r) for r in result]))
        return json.dumps(result)

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def analyzedwordcorpus(self):
        """The analyzedwordcorpus method simply serves the
        analyzedwordcorpus.html page which links to the Javascript
        public/javascript/analyzedwordcorpus.js.  All
        "analyzedwordcorpus_"-prefixed methods are Ajax responders.

        """

        return render('/derived/analysis/analyzedwordcorpus.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def morphotactics(self):
        return render('/derived/analysis/morphotactics.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def morphophonology(self):
        return render('/derived/analysis/morphophonology.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def probabilitycalculator(self):
        return render('/derived/analysis/probabilitycalculator.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def morphologicalparser(self):
        return render('/derived/analysis/morphologicalparser.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def getparse(self):
        """Returns a list of tuples representing the possible parses of the
        input word.

        """

        word = unicode(request.body, 'utf-8')
        parses = getParsesFromFoma(word)
        if parses == [u'']:
            return json.dumps([('NO PARSE', 'NO PARSE')])
        probCalc = getProbCalc()
        if probCalc:
            probs = [probCalc.getProbability(p) for p in parses]
            result = zip(parses, probs)
            result.sort(key=lambda x: x[1])
            result.reverse()
            result = [x[0] for x in result]
        else:
            result = parses
        result = json.dumps([splitBreakFromGloss(a) for a in result])
        return result


    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def savephonology(self):
        """Creates the phonology.foma file as well as phonology_regex.foma,
        compilephonology.sh and phonology.foma.bin.

        """

        phonology = unicode(request.body, 'utf-8')

        # 1. Save phonology.foma file
        log.debug('Writing phonology.foma.')
        phonologyFilePath = os.path.join(analysisDataDir, phonologyFileName)
        phonologyFile = codecs.open(phonologyFilePath, 'w', 'utf-8')
        phonologyFile.write(phonology)
        phonologyFile.close()

        # 2. Save phonology_regex.foma file
        log.debug('Writing phonology_regex.foma.')
        phonologyRegexFilePath = os.path.join(analysisDataDir,
                                              phonologyRegexFileName)
        phonologyRegexFile = codecs.open(phonologyRegexFilePath, 'w', 'utf-8')
        phonologyRegexFile.write('%s\n\nregex phonology;' % phonology)
        phonologyRegexFile.close()

        # 3. Write compilephonology.sh
        log.debug('Writing compilephonology.sh.')
        phonologyBinaryFilePath = os.path.join(analysisDataDir,
                                               phonologyBinaryFileName)
        compilePhonologyPath = os.path.join(
            analysisDataDir, compilePhonologyFileName)
        compilePhonology = open(compilePhonologyPath, 'w')
        cmd = 'foma -e "source %s" -e "save stack %s" -e "quit"' % (
            phonologyRegexFilePath, phonologyBinaryFilePath)
        compilePhonology.write(cmd)
        compilePhonology.close()
        os.chmod(compilePhonologyPath, 0755)

        # 4. Execute compilephonology.sh
        log.debug('Generating phonology.foma.bin.')
        process = subprocess.Popen([compilePhonologyPath], shell=True,
            stdout=subprocess.PIPE)

        now = datetime.utcnow().strftime('at %H:%M on %b %d, %Y')
        output = unicode(process.communicate()[0], 'utf-8')

        success = 'Writing to file %s' % phonologyBinaryFilePath
        if success in output:
            msg = "phonology script saved and compiled (%s)." % now
            return "<span style='color:green;font-weight:bold;'>%s</span>" % msg
        else:
            msg = "phonology script saved but unable to compile."
            return "<span class='warning-message'>%s</span>" % msg

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def generatemorphotactics(self):
        """Writes the morphotactics.foma file representing the morphotactics
        of the language.

        """

        print 'Getting syncatWordStrings.'
        syncatWordStrings = getAllSyncatWordStrings(delim)

        print 'Getting lexicalItems.'
        lexicalItems = getLexicalItems(delim)

        print 'Writing lexicon.txt file.'
        lexiconFilePath = os.path.join(analysisDataDir, lexiconFileName)
        lexiconFile = codecs.open(lexiconFilePath, 'w', 'utf-8')
        lexiconString = u''
        for li in sorted(lexicalItems.keys()):
            lexiconString += u'#%s' % li
            for x in sorted(lexicalItems[li]):
                lexiconString += u'\n%s %s' % (x[0], x[1])
            lexiconString += u'\n\n'
        lexiconFile.write(lexiconString)
        lexiconFile.close()

        print 'Getting fomaMorphotacticsFile.'
        fomaFile = getFomaMorphotacticsFile(
            syncatWordStrings, lexicalItems, delim)
        morphotacticsFilePath = os.path.join(analysisDataDir,
                                             morphotacticsFileName)
        morphotacticsFile = codecs.open(morphotacticsFilePath, 'w', 'utf-8')
        morphotacticsFile.write(fomaFile)
        morphotacticsFile.close()
        
        print 'Done.'
        now = datetime.utcnow().strftime('at %H:%M on %b %d, %Y')
        return "morphotactics file saved (%s)." % now

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def generatemorphophonology(self):
        """This method writes the foma binary file morphophonology.foma.bin
        representing the morphophonology FST.  In order to do so, it also writes
        two other files: morphophonology.foma and compilemorphophonology.sh.
        The Python subprocess module is then used to run the shell script
        compilemorphophonology.sh which runs a series of foma commands that
        result in the creation of the morphohonology.foma.bin file.

        """

        morphophonologyBinaryFilePath = os.path.join(
            analysisDataDir, morphophonologyBinaryFileName)

        # 1. Write morphophonology.foma
        print 'Writing morphophonology.foma.'
        phonologyFilePath = os.path.join(analysisDataDir, phonologyFileName)
        phonologyFile = codecs.open(phonologyFilePath, 'r', 'utf-8')
        phonology = phonologyFile.read()

        morphotacticsFilePath = os.path.join(analysisDataDir,
                                             morphotacticsFileName)
        morphotacticsFile = codecs.open(morphotacticsFilePath, 'r', 'utf-8')
        morphotactics = morphotacticsFile.read()

        morphophonologyFilePath = os.path.join(analysisDataDir,
                                               morphophonologyFileName)
        morphophonologyFile = codecs.open(morphophonologyFilePath, 'w', 'utf-8')
        morphophonology = u'%s\n\n\n%s\n\n\n%s\n\n\n%s' % (
            morphotactics,
            phonology,
            'define morphophonology morphotactics .o. phonology;',
            'regex morphophonology;'
        )
        morphophonologyFile.write(morphophonology)

        # 2. Write compilemorphophonology.sh
        print 'Writing compilemorphophonology.sh.'
        compilePath = os.path.join(analysisDataDir,
                                   compileMorphophonologyFileName)
        compileFile = open(compilePath, 'w')
        cmd = 'foma -e "source %s" -e "save stack %s" -e "quit"' % (
            morphophonologyFilePath, morphophonologyBinaryFilePath)
        compileFile.write(cmd)
        compileFile.close()
        os.chmod(compilePath, 0755)

        # 3. Execute compilemorphophonology.sh
        print 'Generating morphophonology.foma.bin.'
        process = subprocess.Popen([compilePath], shell=True,
            stdout=subprocess.PIPE)

        now = datetime.utcnow().strftime('at %H:%M on %b %d, %Y')
        output = unicode(process.communicate()[0], 'utf-8')
        print 'Done.'

        success = 'Writing to file %s' % morphophonologyBinaryFilePath
        if success in output:
            msg = "morphophonology binary file generated (%s)." % now
            return "<span style='color:green;font-weight:bold;'>%s</span>" % msg
        else:
            msg = "unable to generate morphophonology binary file."
            return "<span class='warning-message'>%s</span>" % msg

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def generateprobabilitycalculator(self):

        print 'Getting lexical items.'
        lexItms = getLexicalItemsFromFile(delim)
        lexCats = lexItms.keys()

        print 'Getting Forms with analyzed words.'
        forms = getFormsWithAnalyzedWords()

        print 'Getting analyzed word tokens.'
        analyzedWords = getAnalyzedWords(forms, lexCats, delim)
        print 'There are %d analyzed words in the database.' % len(
            analyzedWords)

        print 'Writing analyzed_words.txt file.'
        saveAnalyzedWordsFile(analyzedWords)

        print 'Getting ngrams.'
        unigrams, bigrams = getNGramCounts(analyzedWords, lexItms)

        print 'Getting probabilityCalculator.'
        probabilityCalculator = ProbabilityCalculator(unigrams, bigrams, delim)

        print 'Updating application globals with probabilityCalculator.'
        app_globals.wordProbabilityCalculator = probabilityCalculator

        print 'Pickling probabilityCalculator.'
        probabilityCalculatorPicklePath = os.path.join(
            analysisDataDir, probabilityCalculatorFileName)
        probabilityCalculatorPickle = open(
            probabilityCalculatorPicklePath, 'wb')
        pickle.dump(probabilityCalculator, probabilityCalculatorPickle)
        probabilityCalculatorPickle.close()

        print 'Done.'
        now = datetime.utcnow().strftime('at %H:%M on %b %d, %Y')
        msg = 'generated probability calculator (%s)' % now
        return "<span style='color:green;font-weight:bold;'>%s</span>" % msg

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def evaluateparser(self):
        #analyzeAccentation()

        formsFilter = None
        formsFilter = 'frantz'

        print 'Getting lexical items from file.'
        lexItms = getLexicalItemsFromFile(delim)
        lexCats = lexItms.keys()

        if formsFilter:
            print 'Getting Forms with analyzed words.'
            forms = getFormsWithAnalyzedWords()
            if formsFilter == 'frantz':

                badCats = ['vcpx', 'nan', 'nin', 'nar', 'nir', 'vai', 'vii',
                           'vta', 'vti', 'vrt', 'adt', 'dem', 'prev', 'med',
                           'fin', 'oth', 'und', 'pro', 'asp', 'ten', 'mod',
                           'agra', 'agrb', 'thm', 'whq', 'num', 'drt', 'dim',
                           'o', 'stp', 'PN', 'INT']
                forms = [f for f in forms if f.source and
                         f.source.authorLastName == u'Frantz'
                         and (not f.syntacticCategory or
                         f.syntacticCategory.name not in badCats)]
                print 'We are analyzing data from %d forms' % len(forms)

            print 'Getting analyzed word tokens.'
            analyzedWords = getAnalyzedWords(forms, lexCats, delim)
            print 'There are %d analyzed words in the database.' % len(
                analyzedWords)

            print 'Writing analyzed_words_frantz.txt file.'
            saveAnalyzedWordsFile(analyzedWords, 'analyzed_words_frantz.txt')

        else:
            print 'Getting analyzed word tokens from file.'
            analyzedWordsFilePath = os.path.join(analysisDataDir,
                                                 analyzedWordsFileName)
            analyzedWordsFile = codecs.open(analyzedWordsFilePath, 'r', 'utf-8')
            analyzedWords = [tuple(x[:-1].split()) for x in analyzedWordsFile]
            analyzedWordsFile.close()

        print 'Getting training and test sets.'
        trainingSet, testSet = getTrainingAndTestSets(analyzedWords)

        print 'Getting ngrams from training set.'
        unigrams, bigrams = getNGramCounts(trainingSet, lexItms)

        print 'Getting probabilityCalculator based on training set.'
        probCalc = ProbabilityCalculator(unigrams, bigrams, delim)

        def getFScore(results):
            try:
                numCorrectParses = len([x for x in results if x[1] == x[2]])
                numGuesses = len([x for x in results if x[2]])
                numActualParses = len(results)
                P = numCorrectParses / float(numGuesses)
                R = numCorrectParses / float(numActualParses)
                F = (2 * P * R) / (P + R)
            except ZeroDivisionError:
                F = 0.0
            return F

        def printResult(result, F, i):
            rightAnswerInParses = result[1] in result[3]
            correct = result[2] == result[1]
            print '%d. %s %s' % (i, result[0],
                                 {True: 'Correct', False: 'Incorrect'}[correct])
            try:
                print '\tbest guess: %s' % ' '.join(result[2])
            except TypeError:
                print '\tbest guess: NO GUESS'
            print '\tright answer: %s' % ' '.join(result[1])
            print '\tright answer in parses: %s' % rightAnswerInParses
            print '\tF-score: %f' % F

        results = []
        resultsConformingToPhonology = []
        lookup = {}
        i = 1

        for word in testSet:
            tr = word[0]
            tr = removeWordFinalPunctuation(tr) # Remove word-final punctuation
            mb = word[1]
            mg = word[2]
            variants = []
            rightAnswer = (mb, mg)

            conformsToPhonology = False
            phonologizeds = applyFomaPhonology(mb, 'inverse')
            if tr in phonologizeds:
                conformsToPhonology = True
                print '%s phonologizes to %s' % (mb, tr)
            else:
                print '%s does not phonologize to %s, but to %s' % (
                    mb, tr, ', '.join(phonologizeds))

            try:    # If we've already parsed this, no need to do it again
                bestGuess, parses = lookup[tr]
            except KeyError:
                parses = getParsesFromFoma(tr)  # Try to get parses

                if parses == [u'']: # If none, get variants
                    variants = getOrthographicVariants(tr)
                    if tr[0].isupper():
                        deCapped = tr[0].lower() + tr[1:]
                        variants = [deCapped] + \
                            getOrthographicVariants(deCapped) + variants
                    print '\nVariants:\n\t%s\n' % '\n\t'.join(variants)

                for v in variants:
                    print '\t%s is a variant for %s' % (v, tr)
                    parses = getParsesFromFoma(v)
                    if parses != [u'']:
                        print '\tWe got some parses for %s!:\n%d' % (
                            v, len(parses))
                        break
                    else:
                        print '\tNo parses for %s :(' % v

                if parses == [u'']:
                    parses = []
                    bestGuess = None

                if parses:
                    probs = [probCalc.getProbability(p) for p in parses]
                    parses = zip(parses, probs)
                    parses.sort(key=lambda x: x[1])
                    parses.reverse()
                    parses = [splitBreakFromGloss(x[0]) for x in parses]
                    bestGuess = parses[0]

            # Remember results so we don't needlessly reparse 
            lookup[tr] = (bestGuess, parses)

            result = (tr, rightAnswer, bestGuess, parses)
            results.append(result)
            if conformsToPhonology:
                resultsConformingToPhonology.append(result)

            F = getFScore(results)
            print 'All Data:'
            printResult(result, F, i)

            print 'Data where phonology works'
            F = getFScore(resultsConformingToPhonology)
            printResult(result, F, i)

            i += 1

            print '\n\n'


    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def applyphonology(self, id):
        return '<br />'.join(list(set(applyFomaPhonology(id, 'inverse'))))

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def applyphonologytodb(self):

        def getVariants(word):
            deCapped = word[0].lower() + word[1:]
            return list(set([removeExtraneousPunctuation(word),
                    removeExtraneousPunctuation(deCapped)]))

        def getReport(mb, tr, phonologizations):
            report = u''
            if tr in phonologizations or \
            set(getVariants(tr)) & set(phonologizations):
                span = '<span style="color: green;">'
                report += u'<p>%s%s \u2192 %s</span></p>' % (span, mb, tr)
            else:
                span = '<span style="color: red;">'
                report += u'<p>%s%s \u219B %s</span></p>\n<ul>' % (span, mb, tr)
                for ph in phonologizations:
                    report += u'<li>%s</li>' % ph
                report += u'</ul>'
            return report

        output = u''

        # Get forms based on the search/filter provided by the user
        values = urllib.unquote_plus(unicode(request.body, 'utf-8'))
        values = json.loads(values)

        schema = SearchFormForm()
        try:
            result = schema.to_python(values)
        except Invalid:
            return 'Unable to validate form data'

        form_q = meta.Session.query(model.Form)
        form_q = h.filterSearchQuery(result, form_q, 'Form')
        if 'limit' in result and result['limit']:
            form_q = form_q.limit(int(result['limit']))
        forms = form_q.all()
        log.debug(len(forms))

        correct = incorrect = wordsFound = 0
        mb2phonologized = {}
        output += u'<p>%d Forms match your criteria</p>' % len(forms)
        for form in forms:
            tr = form.transcription
            mb = form.morphemeBreak
            if form.morphemeBreak:
                if len(tr.split()) == len(mb.split()):
                    words = zip(tr.split(), mb.split())
                    for w in words:
                        tr = w[0]
                        mb = w[1]
                        try:
                            phonologizations = mb2phonologized[mb]
                        except KeyError:
                            phonologizations = list(set(applyFomaPhonology(
                                mb, 'inverse')))
                            mb2phonologized[mb] = phonologizations
                        wordsFound += 1
                        if tr in phonologizations or \
                        set(getVariants(tr)) & set(phonologizations):
                            correct += 1
                        else:
                            print '%s is not in %s' % (getVariants(tr), str(phonologizations))
                        output += getReport(w[1], w[0], phonologizations)
        try:
            percentCorrect = 100 * correct / float(wordsFound)
        except ZeroDivisionError:
            percentCorrect = 0.0
        output += u'<p>%0.2f%% accuracy.</p>' % percentCorrect
        output += u'<p>(%d words found in %d Forms).</p>' % (wordsFound, len(forms))
        return output
    