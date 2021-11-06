#!/usr/bin/env python3

import argparse
import base64
import hashlib
import os
from collections import defaultdict

def hash_line(s):
    return base64.b64encode(hashlib.sha256(s.encode('utf-8')).digest(), b'-_')[:12].decode('utf-8')

parser = argparse.ArgumentParser('convert a text corpus to apertium-regtest inputs and golds')
parser.add_argument('test', help='test corpus to create or append to')
parser.add_argument('corp', help='input corpus to convert')
parser.add_argument('-d', '--dir', help='location of test directory (default: current directory)', default='.')
parser.add_argument('-s', '--sep', help='separator between input and gold (default: newline)', default='\n')
args = parser.parse_args()

inp = []
gold = defaultdict(list)

with open(args.corp) as fin:
    line_sep = '\n\n' if args.sep == '\n' else '\n'
    txt = fin.read().split(line_sep)
    for line in txt:
        ls = line.strip().split(args.sep)
        if len(ls) < 2:
            continue
        i = ls[0]
        g = ls[1]
        inp.append(i)
        gold[hash_line(i)].append(g)

pth = os.path.join(args.dir, 'test')
if not os.path.isdir(pth):
    os.mkdir(pth)
os.chdir(pth)

with open(args.test + '-input.txt', 'a') as fout:
    fout.write('\n' + '\n'.join(inp))
    print('Inputs written to', os.path.join(pth, args.test + '-input.txt'))

with open(args.test + '-generator-gold.txt', 'a') as fout:
    fout.write('\n')
    for k in sorted(gold.keys()):
        fout.write('[%s]\n' % k)
        fout.write(''.join(g + ' [/option]\n' for g in gold[k]))
        fout.write('[/%s]\n' % k)
    print('Gold values written to', os.path.join(pth, args.test + '-generator-gold.txt'))

print('If either of these is the wrong file, the contents can be safely copied to the end of the correct file(s).')
