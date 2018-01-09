# /usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
import os
import argparse
import unicodedata
import itertools
import string
import pdb
from pynini import *

# Implements Estonian-specific G2P rules
def pronounce_fst(sigma_star):
  t_list = []
  translit = {
    "ž" : "š", 
    "s~" : "š",
    "z~" : "š",
    "ø" : "ö",
    "q" : "k",
    "kk" : "K",
    "pp" : "P",
    "tt" : "T",
    "ph" : "f",
    "x" : "ks",
    "sch" : "š", 
    "cz" : "tš",
    "ici" : "itsi",  
    "zz" : "ts",  
    "w" : "v",
    "y" : "i",
    "z" : "s",
    "ć" : "tš",
    "č" : "tš",
    "ç" : "ts",
    "ĉ" : "tš",
    "c" : "k",
    "jj" : "ij"
    }
  vowel = union(u"a", u"e", u"i", u"o", u"u", u"õ", u"ä", u"ö", u"ü")
  t_list.append(cdrewrite(t("ch", u"tš"), "[BOS]", vowel, sigma_star))
  t_list.append(cdrewrite(t("chr", "kr"), "[BOS]", "", sigma_star))
  t_list.append(cdrewrite(t("ch", "hh"), vowel, "", sigma_star))
  t_list.append(cdrewrite(t("ck", "K"), vowel, "", sigma_star))
  t_list.append(cdrewrite(t("c", "s"), "", "i", sigma_star))
  t_list.append(cdrewrite(t("c", "ts"), u("r", "l", "n"), u("e", "i"), sigma_star))

  t_list.append(cdrewrite(string_map(translit, input_token_type="utf8", output_token_type="utf8").closure(), "", "", sigma_star))

  t_list.append(cdrewrite(t("sh", u"š", input_token_type="utf8", output_token_type="utf8"), vowel, vowel, sigma_star, mode="opt"))
  
  plosive_lc = string_map(list(u"aeiouõäöümnlrv"), input_token_type="utf8", output_token_type="utf8")
  plosive_rc = u(string_map(list(u"lrmnvjaeiouõäöü"), input_token_type="utf8", output_token_type="utf8"), "[EOS]")
  
  t_list.append(cdrewrite(t("k", "K"), plosive_lc, plosive_rc, sigma_star))
  t_list.append(cdrewrite(t("p", "P"), plosive_lc, plosive_rc, sigma_star))
  t_list.append(cdrewrite(t("t", "T"), plosive_lc, plosive_rc, sigma_star))
  
  t_list.append(cdrewrite(t("g", "k"), "", "", sigma_star))
  t_list.append(cdrewrite(t("b", "p"), "", "", sigma_star))
  t_list.append(cdrewrite(t("d", "t"), "", "", sigma_star))
  
  t_list.append(cdrewrite(t("i", "ij"), vowel, difference(vowel, "i"), sigma_star))
  t_list.append(cdrewrite(t("i", "j"), difference(sigma_star, vowel), difference(vowel, "i"), sigma_star))
  
  result = sigma_star
  for t_i in t_list:
    result = result * t_i
  return result.optimize()


def variants_fst(sigma_star):
  vowels = union("a", "e", "i", "o", "u", "õ", "ä", "ö", "ü")
  r1 = u(sigma_star, cdrewrite(t("selle", "sele"), "[BOS]", "", sigma_star))
  r2 = u(sigma_star, cdrewrite(t("nud", "nd"), vowels, "[EOS]", sigma_star))
  r3 = u(sigma_star, cdrewrite(t(u"äe", u"ää", input_token_type="utf8", output_token_type="utf8"), sigma_star, "", sigma_star))
  t_file = string_file(SRC_DIR + "/conf/variants.txt")
  r_file = u(sigma_star, cdrewrite(t_file, "[BOS]", "[EOS]", sigma_star))
  return (r1 * r2 * r3 * r_file).optimize()

def rewrite_fst(sigma_star):
  rewrite_map = {}
  for l in open(SRC_DIR + "/conf/rewrites.txt"):
    ss = l.decode("utf-8").split()
    if len(ss) > 1:
      rewrite_map[ss[0]] = ss[1:]
  result = sigma_star
  for word in sorted(rewrite_map, key=len, reverse=True):
    rewrites = rewrite_map[word]
    combined = None
    for rewrite1 in rewrites:
      r = cdrewrite(t(word, rewrite1), "[BOS]", "", sigma_star)
      if combined is not None:
        combined = u(combined, r)
      else:
        combined = r
    result = (result * combined).optimize()
  return result
   
def number_fst(inflection, sigma_star):
  pass

def spell_fst(sigma_star):
  lowercase_letters = string_map(list(u"abcdefghijklmnoprstuvõäöüxyz"), input_token_type="utf8", output_token_type="utf8")
  numbers = string_map(list(u"1234567890"), input_token_type="utf8", output_token_type="utf8")
  punctuation = string_map(list(u"-'/_"), input_token_type="utf8", output_token_type="utf8")
  t_file = string_file(SRC_DIR + "/conf/letters.map", input_token_type="utf8", output_token_type="utf8")
  result = cdrewrite(t_file.closure(2, 4), u(lowercase_letters, numbers, punctuation, "[BOS]"), u(lowercase_letters, numbers, punctuation, "[EOS]"), sigma_star)

  return result.optimize()

def rmdiacritics(char):

    '''
    Return the base character of char, by "removing" any
    diacritics like accents or curls and strokes and the like.
    '''
    desc = unicodedata.name(unicode(char))
    cutoff = desc.find(' WITH ')
    if cutoff != -1:
        desc = desc[:cutoff]
    try:
      return unicodedata.lookup(desc)
    except:
      return char

if __name__ == '__main__':

  parser = argparse.ArgumentParser(description='Apply G2P rules for Estonian')
  parser.add_argument('--inverse', default=False, action='store_true', help='Use inverse rules')
  parser.add_argument('--fst', default="", help="FST for ranking results")
  parser.add_argument('--nbest', type=int, default=3, help="Max number of hypotheses")
  args = parser.parse_args()

  SRC_DIR = os.path.dirname(os.path.abspath(__file__)) # /a/b/c/d/e

  input_chars = list(u"0123456789-+/_.:'~")
  input_chars.extend(list(u"abcdefghijklmnoprsštuvwõõäöüxyzž"))
  input_chars.extend(u"ćçčĉø")
  input_chars.extend([c.upper() for c in input_chars])
  
  
  
 
  #for i in range(300):
    #try:
      #letter = unichr(i)
      #unicode_name = unicodedata.name(letter)
      
      #if unicode_name.startswith("LATIN CAPITAL LETTER") or unicode_name.startswith("LATIN SMALL LETTER"):
        #input_chars.append(letter)
    #except Exception,e: 
      #pass
  
  sigma_star = string_map(input_chars, input_token_type="utf8", output_token_type="utf8").closure().optimize()


  lowercaser_pairs = {}
  for c in input_chars:
    if c.lower() != c:
      lowercaser_pairs[c] = c.lower()
  lowercaser = string_map(lowercaser_pairs).closure()

  uncapitalizer = cdrewrite(string_map(lowercaser_pairs, input_token_type="utf8", output_token_type="utf8"), "[BOS]", "", sigma_star)

  latin_simplifier_pairs = {}
  for c in input_chars:
    if c.lower() not in set(u'öäõüžš'):
      latin_simplifier_pairs[c] = rmdiacritics(c)
    else:
      latin_simplifier_pairs[c] = c
  latin_simplifier = string_map(latin_simplifier_pairs).closure()

  spell = spell_fst(sigma_star)
  rewrite = rewrite_fst(sigma_star)
  variants = variants_fst(sigma_star)
  pronounce = pronounce_fst(sigma_star)
  
  
  

  transformer = rewrite * uncapitalizer *  variants * pronounce
  transformer.invert().optimize()
  #transformer = pronouncer


  if args.inverse:
    char_lm = Fst.read(args.fst)
    while 1:
      l = sys.stdin.readline()    
      pron = l.decode("utf-8").strip()
      pron = pron.replace("sh", u"š").replace("ou", u"õ").replace("ae", u"ä").replace("oe", u"ö").replace("ue", u"ä").replace("kk", u"K").replace("pp", u"P").replace("tt", u"T").replace(" ", "")
      #result = optimize(l.strip() *  transformer * char_lm)
      orig_word = acceptor(pron, token_type="utf8")
      lattice = optimize(((orig_word * transformer).project(True) * char_lm))
      #print(lattice * char_lm)

      #lattice = optimize(word * char_lm)

      #print(lattice)
      #print(shortestpath((lattice).project(False)).stringify(token_type="utf8"))

      
      for (i, (word, pronunciation, w )) in enumerate(shortestpath(lattice.project(False), nshortest=args.nbest, unique=True).paths(input_token_type="utf8", output_token_type="utf8")):
        variant_id_str = ""
        if i > 0:
          variant_id_str = "(%d)" % (i+1)
        print(orig_word.stringify(token_type="utf8"), pronunciation, w)
        sys.stdout.flush()
  else:
    raise Exception("not implemented")
  
