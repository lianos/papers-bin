#!/usr/bin/env python

"""
Generates rudimentary bibtex file by parsing \cite*{}
references in a document(s), and crossreferences the citekeys
with the ones in your Papers2 databse.

Requires Python >= 2.5 and Papers >= 2.0.8

Minimal BibTex entry looks like so:

@article{Proudfoot:2004gs, citekey
author = {Proudfoot, Nick}, author_string
title = {{New perspectives on connecting ...}}, attributed_title
journal = {Current opinion in cell biology}, bundle_string
year = {2004},  publication_date (99200406011200000000222000)
month = {jun},
volume = {16}, volume
number = {3}, number
pages = {272--278} startpage -- endpage
}

To get the journal name, use the `bundle` column in Pulblication and join it to NameVariant.object_id

select
  p.publication_date, p.author_string, p.attributed_title,
  p.bundle, p.bundle_string, p.volume, p.number, p.startpage,
  p.endpage, n.name
from
  Publication as p
inner join NameVariant as n on p.bundle=n.object_id
where
  p.citekey="Sandberg:2008ks";

Forget the complex query, just use bundle_string for journal name
  
"""
import re, os, time, sys, glob, itertools, sqlite3
from optparse import OptionParser
from ConfigParser import ConfigParser, NoOptionError

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

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

month_xlate = {
 '01' : 'jan', '02' : 'feb', '03' : 'mar', '04' : 'apr',
 '05' : 'may', '06' : 'jun', '07' : 'jul', '08' : 'aug',
 '09' : 'sep', '10' : 'oct', '11' : 'nov', '12' : 'dec'
}
def convert_date(pub_date, month=(6,7), year=(2,5)):
    """99200406011200000000222000 == Jun 2004
    returns (month, year) as strings
    """
    try:
        cmonth = month_xlate[pub_date[month[0]:month[1]+1]]
    except:
        cmonth = ''
    try:
        cyear = pub_date[year[0]:year[1]+1]
    except:
        cyear = ''
    return {'month' : cmonth, 'year' : cyear}

def convert_author_style(author_string, style="default"):
    # return author_string
    if style == "default":
        authors = author_string.replace("and", "").split(',')
        mangled = list()
        for author in authors:
            pieces = author.strip().split()
            lastname = pieces[-1]
            rest = ' '.join(pieces[:-1])
            mangled.append("%s, %s" % (lastname, rest))
        author_string = ' and '.join(mangled)
    return author_string

def lookup_citations(dbconn, citekeys, n=100):
    query = """SELECT publication_date, full_author_string,
               attributed_title, bundle_string, volume, number,
               startpage, endpage, citekey
               FROM Publication WHERE citekey IN (%s)"""
    results = {}
    c = dbconn.cursor()
    while len(citekeys) > 0:
        take = min(len(citekeys), n)
        cites = ['"%s"' % x for x in citekeys[0:take]]
        cites = ','.join(cites)
        citekeys = citekeys[take:]
        c.execute(query % cites)
        for row in c:
            date = convert_date(row['publication_date'])
            citekey = row['citekey']
            entry = {
              'title' : row['attributed_title'],
              'author' : convert_author_style(row['full_author_string']),
              'journal' : row['bundle_string'],
              'citekey' : citekey
            }            
            if date['month'] is not None:
                entry['month'] = date['month']
            if date['year'] is not None:
                entry['year'] = date['year']
            if row['number'] is not None:
                entry['number'] = row['number']
            if row['volume'] is not None:
                entry['volume'] = row['volume']
            if row['startpage'] is not None and row['endpage'] is not None:
                entry['pages'] = "%s--%s" % (row['startpage'], row['endpage'])
            results[citekey] = entry
    return results

def as_bibtex(info):
    result = []
    header = '@article{%s,\n' % info['citekey'].encode('utf-8')
    for key in info:
        if key == 'citekey':
            continue
        if key == 'title':
            add = 'title = {{%s}}' % info['title'].encode('utf-8')
        else:
            add = '%s = {%s}' % (key, info[key].encode('utf-8'))
        result.append(add)
    meta = ",\n".join(result)
    result = header + meta + "\n}"
    return result

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
    parser.add_option('-d', '--dbpath', dest="dbpath",
                      help="The path to the Papers2 sqlite database",
                      default="~/Library/Papers2/Library.papers2/Database.papersdb")
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                      help='Make some noise')
    parser.add_option('-f', '--force', dest='force', default=False,
                      action='store_true',
                      help="Set to force overwrite of existing output bib file")
    (options, args) = parser.parse_args()
    
    if options.out is None:
        to_stdout = True
        outfile = sys.stdout
        report = sys.stderr
    else:
        if os.path.isfile(options.out):
            parser.error("Outfile already exists")
        outfile = open(options.out, 'w')
        report = sys.stdout
        to_stdout = False
    
    dbpath = options.dbpath
    ## override options with values in ~/.papersrc
    config_file = os.path.expanduser('~/.papersrc')
    if os.path.isfile(config_file):
        cparser = ConfigParser()
        cparser.read(config_file)
        try:
            dbpath = cparser.get('appinfo', 'dbpath')
        except NoOptionError:
            pass
    
    ## Check arguments and run
    try:
        # dbconn = connect_database(options.dbpath)
        dbconn = sqlite3.connect(dbpath)
    except:
        parser.error("Can not connect to database: %s" % dbpath)
    dbconn.row_factory = dict_factory
    
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
    
    citations = lookup_citations(dbconn, CITEKEYS.keys())
    
    for citation in citations:
        outfile.write(as_bibtex(citations[citation]))
        outfile.write("\n")
    
    if options.verbose:
        report.write("=== Citekeys Used ===\n")
        for citation in CITEKEYS:
            report.write("%s : %d\n" % (citation, CITEKEYS[citation]))
    
    if not to_stdout:
        outfile.close()

