#!/usr/bin/env python

"""
Generates rudimentary rudimentary bibtex file by parsing \cite*{}
references in a document(s), and crossreferences the citekeys
with the ones in your Papers2 databse.

Requires Python >= 2.5 and Papers >= 2.0.8
"""
import re, os, time, sys, glob, itertools
from optparse import OptionParser

CITEKEYS = {} # This keys are found in Publication.citekey
AUTHORS = {}
JOURNALS = {}
PAPERS = {}

citekey_re = re.compile(r"""\\cite(?:t|p)?\{(.*?)\}""", re.MULTILINE)

def extract_citekeys(text):
    citations = citekey_re.findall(text)
    if len(citations) > 0:
        for citation in citations:
            for citekey in citation.split(','):
                citekey = citekey.strip()
                if citekey not in CITEKEYS:
                    CITEKEYS[citekey] = 1
                else:
                    CITEKEYS[citekey] += 1

def connect_database(dbpath):
    return None

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
    parser.add_option('-d', '--db', dest="dbpath",
                      help="The path to the Papers2 sqlite database",
                      default="~/Library/Papers2/Library.papers2/Database.papersdb")
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                      help='Make some noise')
    
    (options, args) = parser.parse_args()
    
    if options.out is None:
        outfile = sys.stdout
        report = sys.stderr
    else:
        if os.path.isfile(options.out):
            parser.error("Outfile already exists")
        outfile = open(options.out, 'w')
        report = sys.stdout
    
    try:
        dbconn = connect_database(options.dbpath)
    except:
        parser.error("Can not connect to database")
    
    ## match input files and flatten + uniqify potentiall nested list
    infiles = [glob.glob(fn) for fn in args]
    infiles = set(itertools.chain(*infiles))
    
    if options.verbose:
        report.write("Parsing files: " + ','.join(infiles) + "\n")
    
    for infile in infiles:
        if not os.path.isfile(infile):
            if options.verbose:
                report.write("Can't load file %s" % infile)
            continue
        fh = open(infile, 'r')
        for line in fh:
            extract_citekeys(line)
    
    if options.verbose:
        report.write("=== Citekeys Used ===\n")
        for citation in CITEKEYS:
            report.write("%s : %d\n" % (citation, CITEKEYS[citation]))
    
