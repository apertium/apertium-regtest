#!/usr/bin/env python3

import base64
from collections import defaultdict
from functools import partial
import hashlib
from http import HTTPStatus
import http.server
import json
import math
import os
import re
import shlex
import socketserver
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree
import zlib

def hash_line(s):
    return base64.b64encode(hashlib.sha256(s.encode('utf-8')).digest(), b'-_')[:12].decode('utf-8')

def load_input(fname):
    with open(fname, 'r') as fin:
        lines = fin.read().splitlines()
        ret = {}
        for i, l_ in enumerate(lines):
            # TODO: more careful escape handling
            l = l_.split('#')[0].replace('\\n', '\n').strip()
            if not l:
                continue
            ret[hash_line(l)] = [i, l]
        return ret

# [hash#line] content [/hash]
txt_out_format = re.compile(r'\[([A-Za-z0-9_-]+)#(\d+)\](.*)\[/\1\]', re.DOTALL)
# [hash] content [/hash]
txt_gold_format = re.compile(r'\[([A-Za-z0-9_-]+)\](.*)\[/\1\]', re.DOTALL)

def load_output(fname):
    try:
        with open(fname, 'r') as fin:
            ret = {}
            txt = fin.read().replace('\0', '')
            for hsh, line, content_ in txt_out_format.findall(txt):
                content = content_.strip()
                if not content:
                    print('ERROR: Entry %s in %s was empty!' % (hsh, fname))
                    sys.exit(1)
                ret[hsh] = [int(line), content]
            return ret
    except FileNotFoundError:
        return {}

def save_output(fname, data, sep='\n'):
    with open(fname, 'w') as fout:
        for inhash in sorted(data.keys()):
            fout.write('[%s#0] %s\n[/%s]\n' % (inhash, data[inhash][1], inhash))

def load_gold(fname):
    try:
        with open(fname, 'r') as fin:
            ret = {}
            for hsh, content in txt_gold_format.findall(fin.read()):
                opts = []
                for o in content.split('[/option]'):
                    o2 = o.strip()
                    if o2:
                        opts.append(o2)
                if not opts:
                    print('ERROR: Empty entry %s in %s' % (ident, fname))
                    sys.exit(1)
                ret[hsh].append(opts)
            return ret
    except FileNotFoundError:
        return {}

def save_gold(fname, data, sep='\n'):
    with open(fname, 'w') as fout:
        for inhash in sorted(data.keys()):
            fout.write('[%s]\n' % inhash)
            for ln in sorted(data[inhash]):
                fout.write('%s [/option]\n' % ln)
            fout.write('[/%s]\n' % inhash)

class Step:
    prognames = {
        'cg-proc': 'disam',
        'apertium-tagger': 'tagger',
        'apertium-pretransfer': 'pretransfer',
        'lrx-proc': 'lex',
        'apertium-transfer': 'chunker',
        'apertium-interchunk': 'interchunk',
        'apertium-postchunk': 'postchunk',
        'lsx-proc': 'autoseq',
        'rtx-proc': 'transfer',
        'apertium-anaphora': 'anaph'
    }
    morphmodes = {
        '-b': 'biltrans',
        '-p': 'postgen',
        '-g': 'generator'
    }
    def __init__(self, xml):
        pr = shlex.split(xml.attrib['name'])
        self.prog = pr[0]
        self.args = pr[1:]
        for ar in xml:
            if ar.tag == 'arg':
                self.args += shlex.split(ar.attrib['name'])
            else:
                self.args.append(ar.attrib['name'])
        for ar in self.args:
            if ar == '$1' or ar == '$2':
                ar = '-g'
        self.name = xml.attrib.get('debug-suff', 'unknown')
        if self.name == 'unknown':
            if self.prog in Step.prognames:
                self.name = Step.prognames[self.prog]
            elif self.prog in ['lt-proc', 'hfst-proc']:
                self.name = 'morph'
                for op in Step.morphmodes:
                    if op in self.args:
                        self.name = Step.morphmodes[op]
    def run(self, in_name, out_name, first=False):
        cmd = [self.prog] + self.args
        print('running', cmd)
        if self.prog in Step.prognames or self.prog in ['lt-proc', 'hfst-proc']:
            cmd.append('-z')
        with open(in_name, 'r') as fin:
            if first:
                data = load_input(in_name)
                txt = ''
                for hsh, (line, content) in data.items():
                    txt += '[%s#%s] %s\n[/%s]\n\0' % (hsh, line, content, hsh)
            else:
                txt = fin.read()
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE)
            stdout, stderr = proc.communicate(txt.encode('utf-8'))
            with open(out_name, 'wb') as fout:
                fout.write(stdout)

class Mode:
    all_modes = {}
    def __init__(self, xml):
        self.name = xml.attrib['name']
        self.steps = [Step(s) for s in xml[0]]
        nm = defaultdict(lambda: 0)
        for s in self.steps:
            nm[s.name] += 1
            if nm[s.name] > 1:
                s.name += str(nm[s.name])
        Mode.all_modes[self.name] = self
    def run(self, corpusname, filename):
        print('run(%s, %s)' % (corpusname, filename))
        fin = filename
        for i, step in enumerate(self.steps):
            fout = 'test/%s-%s-output.txt' % (corpusname, step.name)
            step.run(fin, fout, first=(i == 0))
            fin = fout
        with open(fin, 'r') as f1:
            with open('test/%s-all-output.txt' % corpusname, 'w') as f2:
                f2.write(f1.read())
    def get_commands(self):
        return [s.name for s in self.steps]

def load_modes():
    try:
        root = xml.etree.ElementTree.parse('modes.xml').getroot()
    except FileNotFoundError:
        print('modes.xml not found.')
        print('Please ensure that apertium-regtest is being run in an Apertium directory.')
        sys.exit(1)
    except xml.etree.ElementTree.ParseError as e:
        print('Unable to parse modes.xml.')
        print('Parser message: %s' % e.msg)
        sys.exit(1)
    for m in root:
        Mode(m)

def get_url(remote):
    proc = subprocess.run(['git', 'remote', 'get-url', remote],
                          stdout=subprocess.PIPE)
    if proc.returncode != 0:
        return ''
    return proc.stdout.decode('utf-8').strip()

def yes_no(msg):
    ans = input(msg + ' (yes/no) ')
    while True:
        if 'yes'.startswith(ans.strip().lower()):
            return True
        elif 'no'.startswith(ans.strip().lower()):
            return False
        else:
            ans = input('unable to interpret reply - please type yes or no: ')

def check_git():
    # look for an external git repo
    # return True if we end up cloning it
    proc = subprocess.run(['git', 'remote'], stdout=subprocess.PIPE)
    if proc.returncode != 0:
        return False
    all_remotes = proc.stdout.decode('utf-8').strip().split()
    if len(all_remotes) == 0:
        return False
    url = ''
    if 'origin' in all_remotes:
        url = get_url('origin')
    if not url:
        for remote in all_remotes:
            url = get_url('origin')
            if url:
                break
    if not url:
        return False
    url = url.replace('/apertium-', '/test-')
    ans = yes_no('Test corpora not found. Clone external test corpus?')
    if not ans:
        return False
    inurl = input('remote url (default %s): ' % url).strip()
    if not inurl:
        inurl = url
    proc = subprocess.run(['git', 'clone', inurl, 'test'])
    if proc.returncode == 0:
        return True
    else:
        print('Cloning failed. Please check the remote url and try again.')
        sys.exit(1)

class Corpus:
    all_corpora = {}
    def __init__(self, name, blob):
        # TODO: more error checking, start-step, command
        self.name = name
        self.mode = blob['mode']
        self.infile = 'test/' + blob['input']
        self.data = {}
        self.loaded = False
        self.unsaved = set()
        Corpus.all_corpora[name] = self
    def run(self):
        Mode.all_modes[self.mode].run(self.name, self.infile)
        self.loaded = False
    def exp_name(self, cmd):
        return 'test/%s-%s-expected.txt' % (self.name, cmd)
    def out_name(self, cmd):
        return 'test/%s-%s-output.txt' % (self.name, cmd)
    def gold_name(self, cmd):
        return 'test/%s-%s-gold.txt' % (self.name, cmd)
    def save(self):
        for blob in self.data['cmds']:
            if blob['cmd'] in self.unsaved:
                save_output(self.exp_name(blob['cmd']), blob['expect'])
        self.unsaved = set()
    def load(self):
        if self.loaded:
            return
        ins = load_input(self.infile)
        outs = []
        cmds = Mode.all_modes[self.mode].get_commands()
        self.data = {
            'inputs': ins,
            'cmds': [],
            'count': len(ins)
        }
        for c in cmds:
            expfile = self.exp_name(c)
            outdata = load_output(self.out_name(c))
            expdata = {}
            if os.path.isfile(expfile):
                expdata = load_output(expfile)
            else:
                save_output(expfile, outdata)
                expdata = outdata
            golddata = {}
            goldfile = self.gold_name(c)
            if os.path.isfile(goldfile):
                golddata = load_gold(goldfile)
            if not outs:
                outs = expdata.keys()
            self.data['cmds'].append({
                'cmd': c,
                'opt': c,
                'output': outdata,
                'expect': expdata,
                'gold': golddata,
                'trace': {} # TODO?
            })

        add = [k for k in ins if k not in outs]
        delete = [k for k in outs if k not in ins]
        add.sort(key = lambda x: ins[x][0])
        delete.sort()
        self.data['add'] = add
        self.data['del'] = delete
    def accept_add_del(self, should_save=True):
        if not ('add' in self.data or 'del' in self.data):
            return []
        changes = []
        for blob in self.data['cmds']:
            for a in self.data['add']:
                if a not in blob['expect']:
                    blob['expect'][a] = [0, blob['output'][a][1]]
                    changes.append(a)
                    self.unsaved.add(blob['cmd'])
            for d in self.data['del']:
                if d in blob['expect']:
                    del blob['expect'][d]
                    changes.append(d)
                    self.unsaved.add(blob['cmd'])
        if should_save:
            self.save()
        self.data['add'] = []
        self.data['del'] = []
        return list(set(changes))
    def accept(self, hashes=None, last_step=None):
        if 'cmds' not in self.data:
            return []
        changes = self.accept_add_del(False)
        for blob in self.data['cmds']:
            for h in (hashes or blob['expect'].keys()):
                if blob['expect'][h][1] != blob['output'][h][1]:
                    blob['expect'][h][1] = blob['output'][h][1]
                    changes.append(h)
                    self.unsaved.add(blob['cmd'])
            if blob['cmd'] == last_step:
                break
        self.save()
        return list(set(changes))
    def set_gold(self, hsh, vals, step=None):
        idx = -1
        if step:
            for i, blob in enumerate(self.data['cmds']):
                if blob['cmd'] == step:
                    idx = i
                    break
        self.data['cmds'][idx]['gold'][hsh] = vals
        save_gold(self.gold_name(self.data['cmds'][idx]['cmd']),
                  self.data['cmds'][idx]['gold'])

def load_corpora():
    if not os.path.isdir('test') or not os.path.isfile('test/tests.json'):
        if os.path.isdir('.git'):
            if check_git():
                load_corpora()
                return
        print('Test corpora not found. Please create test/tests.json')
        print('as described at https://wiki.apertium.org/wiki/User:Popcorndude/Regression-Testing')
        sys.exit(1)
    with open('test/tests.json') as ts:
        try:
            blob = json.load(ts)
            for k in blob:
                Corpus(k, blob[k])
        except json.JSONDecoderError as e:
            print('test/tests.json is not a valid JSON document. First error on line %s' % e.lineno)
            sys.exit(1)

def test_run(corpora):
    ls = corpora
    if '*' in corpora:
        ls = list(Corpus.all_corpora.keys())
    for name in ls:
        Corpus.all_corpora[name].run()
    return True, ''

def cb_load(page):
    changes = {
        'changed_final': [],
        'changed_any': [],
        'unchanged': []
    }
    state = {
        '_step': 25, # TODO
        '_count': 0,
        '_ordered': []
    }
    for name, corpus in Corpus.all_corpora.items():
        corpus.load()
        state[name] = corpus.data
        state['_count'] += state[name]['count']
    state['_pages'] = math.ceil(state['_count']/25) # TODO
    return {'state': state}

class CallbackRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        if parts.path.strip('/') != 'callback':
            return super().do_GET()
        else:
            params = urllib.parse.parse_qs(parts.query)
            self.do_callback(params)

    def do_POST(self):
        ln = int(self.headers['Content-Length'])
        data = self.rfile.read(ln)
        self.do_callback(urllib.parse.parse_qs(data.decode('utf-8')))

    def do_callback(self, params):
        print(params)
        if 'a' not in params:
            resp = 'Parameter a must be passed!'
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", 'text/plain')
            self.send_header("Content-Length", len(resp))
            self.end_headers()
            self.wfile.write(resp.encode('utf-8'))
            return

        status = HTTPStatus.OK
        resp = {}

        if params['a'][0] == 'init':
            resp['folder'] = os.path.basename(os.getcwd())
            resp['corpora'] = list(sorted(Corpus.all_corpora.keys()))
        elif params['a'][0] == 'load':
            #try:
            resp = cb_load(params['p'][0])
            #except:
            #    resp['error'] = 'Current state is missing or invalid. You will need to run the regression test for all corpora.'
        elif params['a'][0] == 'run':
            good, output = test_run(params.get('c', ['*']))
            resp['good'] = good
            resp['output'] = output
        elif params['a'][0] == 'accept-nd':
            # TODO: error checking
            resp['c'] = params['c'][0]
            resp['hs'] = Corpus.all_corpora[resp['c']].accept_add_del()
        elif params['a'][0] == 'accept':
            resp['c'] = params['c'][0]
            s = params.get('s', [None])[0]
            hs = []
            if 'hs' in params:
                hs = params['hs'][0].split(';')
            resp['hs'] = Corpus.all_corpora[resp['c']].accept(hs, s)
        elif params['a'][0] == 'gold':
            corp = params['c'][0]
            hsh = params['h'][0]
            golds = json.loads(params['gs'][0])
            stp = None
            if 's' in params:
                stp = params['s'][0]
            Corpus.all_corpora[corp].set_gold(hsh, golds, stp)
            resp = {'c': corp, 'hs': [hsh]}
        else:
            resp['error'] = 'unknown value for parameter a'
        print(resp)

        rstr = json.dumps(resp).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', len(rstr))
        self.end_headers()
        self.wfile.write(rstr)

def start_server():
    d = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/')
    handle = partial(CallbackRequestHandler, directory=d)
    with socketserver.TCPServer(('', 3000), handle) as httpd:
   	    httpd.serve_forever()

if __name__ == '__main__':
    load_modes()
    load_corpora()
    start_server()
