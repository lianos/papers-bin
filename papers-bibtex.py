#!/usr/bin/env python

"""
Generates rudimentary rudimentary bibtex file by parsing \cite*{}
references in a document(s), and crossreferences the citekeys
with the ones in your Papers2 databse.

Requires Python >= 2.5 and Papers >= 2.0.8
"""
import re, os, time, sys
from optparse import OptionParser

if __name__ == '__main__':
    usage = """usage: %prog [OPTIONS] FILE1 [FILES ...]
    
    Parses the file(s) identified by the unix blob-like matching patterns
    provided in the positional arguments for cite*{...} commands in
    them and generates a minimal bibtex file for them by looking up
    the citekeys in your Papers2 database.
    
    If a -o/--out BIBFILE.tex option is not provided, the bibtex file will
    be streamed to STDOUT.
    """
    parser = OptionParser(usage=usage)
    parser.add_option('-o', '--out', dest="out", default=None,
                      help="The file to save the output to, defaults " \
                           "to STDOUT")
    parser.add_optoin('-d', '--db', dest="db",
                      help="The path to the Papers2 sqlite database",
                      default="~/Library/Papers2/Library.papers2/Database.papersdb")
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                      help='Make some noise')
    
    (options, args) = parser.parse_args()
    
    if options.out is None:
        outfile = sys.stdout
    else:
        if os.path.isfile(options.out):
            parser.error("Outfile already exists")
        outfile = open(options.out, 'w')
    
    try:
        dbconn = connect_database()
    except:
        parser.error("Can not connect to database")
    
    ## TODO
    ##   generate file list to read
    ##   extract \cite*
    ##   generate bibtex entries
    