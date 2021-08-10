#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
import os

parser = argparse.ArgumentParser('convert flat apertium-regtest directory to one with subfolders')
args = parser.parse_args()

if not os.path.isdir('test'):
    print('test/ not found.')
    print('Please run this script from the top level of an Apertium directory.')
    sys.exit(1)

os.mkdir('test/output')
os.mkdir('test/gold')
os.mkdir('test/expected')

replace = {
    '-output.txt': 'test/output/',
    '-gold.txt': 'test/gold/',
    '-expected.txt': 'test/expected/'
}

for fname in os.listdir('test'):
    for old, new in replace.items():
        if fname.endswith(old):
            os.rename('test/'+fname, new+fname[:-len(old)]+'.txt')

tests = {}
if os.path.isfile('test/tests.json'):
    with open('test/tests.json') as fin:
        tests = json.loads(fin.read())
tests['settings'] = {'structure': 'nested'}
with open('test/tests.json', 'w') as js:
    js.write(json.dumps(tests, indent=4) + '\n')

txt = ''
end = '\n'
if os.path.isfile('.gitignore'):
    with open('.gitignore') as fin:
        txt = fin.read()
        if '\r\n' in txt:
            end = '\r\n'
        if not txt.endswith(end):
            txt += end
txt += '/test/output' + end
with open('.gitignore', 'w') as fout:
    fout.write(txt)

subprocess.run(['git', 'add', '.gitignore', 'test/tests.json'])
subprocess.run(['git', 'add', 'test'])
