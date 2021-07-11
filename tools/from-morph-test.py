#!/usr/bin/env python3

import argparse
import base64
import hashlib
import json
import os
import yaml

def hash_line(s):
    return base64.b64encode(hashlib.sha256(s.encode('utf-8')).digest(), b'-_')[:12].decode('utf-8')

parser = argparse.ArgumentParser('convert morph-test yaml files to apertium-regtest directories')
parser.add_argument('lang', help='ISO code of language')
parser.add_argument('yaml', help='file to convert')
parser.add_argument('-d', '--dir', help='location of test directory (default: cwd)', default='.')
args = parser.parse_args()

new_tests = {}

def do_test(name, tst):
    analysis = []
    surf = []
    for k_, v_ in tst.items():
        k = '^' + k_ + '$'
        v = v_ if isinstance(v_, str) else v_[0]
        surf.append((v, hash_line(k)))
        analysis.append((k, hash_line(v)))
    if len(surf) == 0:
        return
    with open('%s-input.txt' % name, 'w') as fout:
        surf.sort()
        for s, h in surf:
            fout.write(s + '\n')
    with open('%s-gen-generator-gold.txt' % name, 'w') as fout:
        surf.sort(key=lambda x: x[1])
        for s, h in surf:
            fout.write('[%s]\n%s [/option]\n[/%s]\n' % (h, s, h))
    with open('%s-gen-input.txt' % name, 'w') as fout:
        analysis.sort()
        for a, h in analysis:
            fout.write(a + '\n')
    with open('%s-morph-gold.txt' % name, 'w') as fout:
        analysis.sort(key=lambda x: x[1])
        for a, h in analysis:
            fout.write('[%s]\n%s [/option]\n[/%s]\n' % (h, a, h))
    global new_tests, args
    new_tests[name] = {
        'input': '%s-input.txt' % name,
        'mode': '%s-morph' % args.lang
    }
    new_tests[name + '-gen'] = {
        'input': '%s-gen-input.txt' % name,
        'mode': '%s-gener' % args.lang
    }

with open(args.yaml) as fin:
    pth = os.path.join(args.dir, 'test')
    if not os.path.isdir(pth):
        os.mkdir(pth)
    os.chdir(pth)
    blob = yaml.load(fin.read(), yaml.BaseLoader)
    for name, tst in blob['Tests'].items():
        do_test(name.replace(' ', '_').replace('/', '_'), tst)
if os.path.isfile('tests.json'):
    with open('tests.json') as fin:
        new_tests.update(json.loads(fin.read()))
with open('tests.json', 'w') as js:
    js.write(json.dumps(new_tests))
