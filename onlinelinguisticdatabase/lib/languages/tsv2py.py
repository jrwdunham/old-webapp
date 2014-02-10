"""This module opens a local iso_639_3.tab file, converts its tab-delimited
values to a tuple of tuples and writes a python file (called iso_639_3.py) that
declares a 'langugages' variable which points to the tuple generated.
Controllers can then import the languages tuple with::

    from lib.languages.iso_639_3 import languages

This is a hacky way of allowing websetup.py to import the ISO 639-3 languages
data as a python tuple instead of parsing the .tab (text) file, which is what
the code used to do until I realized that hard-coded absolute paths cause a bug
when the OLD is installed as a package.  I have only now figured out how to
specify the application's root directory in a flexible manner (see below).
However, I am uncertain whether the first approach (parsing the text) is
superior in performance to the new hacky way.  The text-parsing approach has the
benefit of reducing coding configuration so I should probably change back.

The solution to the above::

    iso_639_3AbsPath = os.path.join(
        config['pylons.paths']['root'],
        'lib',
        'languages',
        'iso_639_3.tab'
        )
    iso_639_3 = codecs.open(iso_639_3AbsPath, 'r', 'utf-8')

"""

import codecs
import pickle

inputFile = codecs.open('iso_639_3.tab', 'r', 'utf-8')
outputFile = codecs.open('iso_639_3.py', 'w', 'utf-8')
temp = [tuple(x.split('\t')) for x in inputFile]
output = 'languages = (\n\t'
output += ',\n\t'.join([repr(x) for x in temp])
output += '\n)'
outputFile.write(output)