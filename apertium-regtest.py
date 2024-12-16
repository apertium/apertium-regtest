#!/usr/bin/env python3

import base64
import cmd
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
import threading
import time
import urllib.parse
import urllib.request
import shutil
import xml.etree.ElementTree
import zlib

def hash_line(s):
    return base64.b64encode(hashlib.sha256(s.encode('utf-8')).digest(), b'-_')[:12].decode('utf-8')

class InputFileDoesNotExist(FileNotFoundError):
    pass
class InputFileIsEmpty(Exception):
    pass
class ErrorInPipeline(Exception):
    pass

def ensure_javascript(spath):
    if not os.path.exists(spath + '/bootstrap.css') or not os.path.exists(spath + '/bootstrap.js') or not os.path.exists(spath + '/jquery.js') or not os.path.exists(spath + '/diff.js'):
        print('Downloading Bootstrap, jQuery, and jsDiff from the jsDelivr CDN')
        with urllib.request.urlopen('https://cdn.jsdelivr.net/npm/bootstrap@5.1/dist/css/bootstrap.min.css') as response, open(spath + '/bootstrap.css', 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        with urllib.request.urlopen('https://cdn.jsdelivr.net/npm/bootstrap@5.1/dist/js/bootstrap.min.js') as response, open(spath + '/bootstrap.js', 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        with urllib.request.urlopen('https://cdn.jsdelivr.net/npm/jquery@3.6/dist/jquery.min.js') as response, open(spath + '/jquery.js', 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        with urllib.request.urlopen('https://cdn.jsdelivr.net/npm/diff@4.0/dist/diff.min.js') as response, open(spath + '/diff.js', 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

def load_input(fname):
    try:
        with open(fname, 'r') as fin:
            lines = fin.read().splitlines()
            ret = {}
            for i, l_ in enumerate(lines):
                ls = l_.split('#')
                l = ls.pop(0)
                while l.endswith('\\') and ls:
                    l = l[:-1] + ls.pop(0)
                l = l.replace('\\n', '\n').strip()
                if not l:
                    continue
                ret[hash_line(l)] = [i, l]
            if len(ret) == 0:
                print('ERROR: Input file %s was empty!' % fname)
                raise InputFileIsEmpty(fname)
            return ret
    except FileNotFoundError:
        print('ERROR: Input file %s does not exist!' % fname)
        raise InputFileDoesNotExist(fname)

def load_input_string(fname):
    txt = ''
    for hsh, (line, content) in load_input(fname).items():
        txt += '[%s#%s] %s\n[/%s]\n\0' % (hsh, line, content, hsh)
    return txt

# [hash(#line)?] content [/hash]
hash_format = re.compile(r'\[([A-Za-z0-9_-]+)(#\d+|)\](.*?)\[/\1\]', re.DOTALL)
# the line number is completely useless, but it now appears
# in the expected files in 365 repositories, so we need to still
# parse it - 2021-07-23

def load_output(fname, should_sort_analyses=False):
    try:
        with open(fname, 'r') as fin:
            ret = {}
            txt = fin.read().replace('\0', '')
            for hsh, line, content_ in hash_format.findall(txt):
                content = content_.strip()
                if not content:
                    print('ERROR: Entry %s in %s was empty!' % (hsh, fname))
                if should_sort_analyses:
                    content = sort_analyses(content)
                l = 0
                if line:
                    l = int(line[1:])
                ret[hsh] = [l, content]
                # line numbers are nice for debugging,
                # but nothing breaks if we don't have them
            return ret
    except FileNotFoundError:
        return {}

def save_output(fname, data):
    with open(fname, 'w') as fout:
        for inhash in sorted(data.keys()):
            fout.write('[%s#0] %s\n[/%s]\n' % (inhash, data[inhash][1], inhash))

def load_gold(fname):
    try:
        with open(fname, 'r') as fin:
            ret = {}
            for hsh, line, content in hash_format.findall(fin.read()):
                opts = []
                for o in content.split('[/option]'):
                    o2 = o.strip()
                    if o2:
                        opts.append(o2)
                if not opts:
                    print('ERROR: Empty entry %s in %s' % (hsh, fname))
                    continue
                ret[hsh] = opts
            return ret
    except FileNotFoundError:
        return {}

def save_gold(fname, data):
    with open(fname, 'w') as fout:
        for inhash in sorted(data.keys()):
            fout.write('[%s]\n' % inhash)
            for ln in sorted(set(data[inhash])):
                fout.write('%s [/option]\n' % ln)
            fout.write('[/%s]\n' % inhash)

apertium_wblank_pat = (r'(?:\[\[' +   # [[
                       ('(?:' +
                        r'[^\]\\]|' + # not ] or \\
                        r'\\.|' +     # or an escaped character
                        r'\](?!\])' + # ] not followed by ]
                        ')*') +
                       r'\]\])')      # ]]
apertium_superblank_pat = (r'(?:\[' +     # [
                           ('(?:' +
                            r'[^\]\\]|' + # not ] or \\
                            r'\\.' +      # or an escaped character
                            ')*') +
                           r'\])')        # ]
apertium_blank_pat = ('(?:' +
                      r'[^\[\]\\^]|' + # not []\^
                      apertium_superblank_pat +
                      ')*' +
                      apertium_wblank_pat +
                      '?')
apertium_blank_regex = re.compile(apertium_blank_pat)

def sort_analyses(instr):
    ret = ''
    s = instr
    while s:
        m = apertium_blank_regex.match(s)
        ret += s[:m.end()]
        s = s[m.end():]
        if s and s[0] == '^':
            pieces = []
            last = 0
            esc = False
            for i in range(len(s)):
                if esc:
                    esc = False
                    continue
                elif s[i] == '\\':
                    esc = True
                elif s[i] == '/':
                    pieces.append(s[last:i])
                    last = i+1
                elif s[i] == '$':
                    pieces.append(s[last:i])
                    s = s[i+1:]
                    break
            else:
                ret += s
                s = ''
                break
            ret += pieces[0]
            if len(pieces) > 1:
                ret += '/'
                ret += '/'.join(sorted(pieces[1:]))
            ret += '$'
    ret += s # if something goes wrong, return the rest of the string as-is
    return ret

def run_command(cmd, intxt, outfile, shell=False):
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, shell=shell)
    stdout, stderr = proc.communicate(intxt.encode('utf-8'))
    if proc.returncode != 0:
        c = cmd if isinstance(cmd, str) else ' '.join(cmd)
        print('Failed command: %s' % c)
        print('Writing stderr to test/error.log')
        with open('test/error.log', 'ab') as fout:
            fout.write(('Command: %s\n' % c).encode('utf-8'))
            fout.write(('Output file: %s\n' % outfile).encode('utf-8'))
            fout.write(('Time: %s\n' % time.asctime()).encode('utf-8'))
            fout.write(b'Stdin:\n\n')
            fout.write(intxt.encode('utf-8'))
            fout.write(b'Stdout:\n\n')
            fout.write(stdout)
            fout.write(b'Stderr:\n\n')
            fout.write(stderr)
            fout.write(b'\n\n')
        print('Exiting')
        raise ErrorInPipeline(c)
    else:
        with open(outfile, 'wb') as fout:
            if not intxt:
                h = hash_line(intxt)
                stdout = ('[%s#0]\n' % h).encode('utf-8') + stdout
                stdout += ('\n[/%s]\n' % h).encode('utf-8')
            fout.write(stdout)

def ensure_dir_exists(name):
    pth = os.path.join('test', name)
    if not os.path.isdir(pth):
        os.mkdir(pth)

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
        'apertium-anaphora': 'anaph',
        'cg-conv': 'convert',
        'vislcg3': 'disam',
        'apertium-extract-caps': 'decase',
        'apertium-restore-caps': 'recase'
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
        remove = []
        for i in range(len(self.args)):
            if self.args[i] == '$1':
                self.args[i] = '-g'
            elif self.args[i] == '$2':
                remove.append(i)
        remove.reverse()
        for i in remove:
            self.args.pop(i)
        self.name = xml.attrib.get('debug-suff', 'unknown')
        if self.name == 'unknown':
            if self.prog == 'lsx-proc' and '-p' in self.args:
                self.name = 'postgen'
            elif self.prog in Step.prognames:
                self.name = Step.prognames[self.prog]
            elif self.prog in ['lt-proc', 'hfst-proc']:
                self.name = 'morph'
                for op in Step.morphmodes:
                    if op in self.args:
                        self.name = Step.morphmodes[op]
    def run(self, in_name, out_name, first=False):
        cmd = [self.prog]
        if self.prog in Step.prognames or self.prog in ['lt-proc', 'hfst-proc']:
            if self.prog not in ['cg-conv', 'vislcg3']:
                cmd.append('-z')
        cmd += self.args # -z needs to be before file names
        txt = ''
        if first:
            txt = load_input_string(in_name)
        else:
            with open(in_name, 'r') as fin:
                txt = fin.read()
        if self.prog == 'vislcg3':
            txt = txt.replace('\0', '\n<STREAMCMD:FLUSH>\n')
        run_command(cmd, txt, out_name)

class Mode:
    all_modes = {}
    def __init__(self, xml):
        self.name = xml.attrib['name']
        self.steps = [Step(s) for s in xml[0]]
        self.commands = {}
        nm = defaultdict(lambda: 0)
        for i, s in enumerate(self.steps):
            nm[s.name] += 1
            if nm[s.name] > 1:
                s.name += str(nm[s.name])
            self.commands[s.name] = i
        Mode.all_modes[self.name] = self
    def run(self, corpusname, filename, start=None, flat=True):
        fname = 'test/'
        if flat:
            fname += '%s-%s-output.txt'
        else:
            ensure_dir_exists('output')
            fname += 'output/%s-%s.txt'
        fin = filename
        idx = self.commands.get(start, 0)
        for i, step in enumerate(self.steps[idx:]):
            fout = fname % (corpusname, step.name)
            step.run(fin, fout, first=(i == 0))
            fin = fout
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
        try:
            Mode(m)
        except:
            print('Unable to parse modes.xml.')
            print('Run `apertium-validate-modes` for more information.')
            sys.exit(1)

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
    flat = True
    all_corpora = {}
    def __init__(self, name, blob):
        self.name = name
        self.mode = blob.get('mode', None)
        self.shell = blob.get('command', None)
        if not self.mode and not self.shell:
            print('Corpus %s must specify either "mode": or "command":' % self.name)
            sys.exit(1)
        if self.mode and self.mode not in Mode.all_modes:
            print('Unknown mode %s in corpus %s' % (self.mode, self.name))
            sys.exit(1)
        if 'input' not in blob:
            print('Corpus %s must specify an input file' % self.name)
            sys.exit(1)
        self.infile = None
        if blob['input'] != None:
            self.infile = 'test/' + blob['input']
        elif self.shell:
            pass
        else:
            print('Corpus %s has empty input with standard mode' % self.name)
            sys.exit(1)
        self.start_step = blob.get('start-step', None)
        self.data = {}
        self.loaded = False
        self.unsaved = set()
        self.command_list = ['all']
        if self.mode:
            self.command_list = Mode.all_modes[self.mode].get_commands()
        self.sort = []
        if 'sort' in blob:
            if isinstance(blob['sort'], list):
                self.sort = blob['sort']
            elif blob['sort']:
                self.sort = self.command_list
        self.commands = {c:i for i, c in enumerate(self.command_list)}
        self.relevant_commands = blob.get('relevant', [self.command_list[-1]])
        if not isinstance(self.relevant_commands, list):
            print('Corpus %s specified a non-list for "relevant"' % self.name)
            sys.exit(1)
        self.hashes = []
        Corpus.all_corpora[name] = self
    def __len__(self):
        return len(self.hashes)
    def run(self):
        if self.mode:
            Mode.all_modes[self.mode].run(self.name, self.infile,
                                          start=self.start_step,
                                          flat=Corpus.flat)
        else:
            txt = ''
            if self.infile:
                txt = load_input_string(self.infile)
            run_command(self.shell, txt, self.out_name('all'), shell=True)
        self.loaded = False
    def exp_name(self, cmd):
        if Corpus.flat:
            return 'test/%s-%s-expected.txt' % (self.name, cmd)
        else:
            return 'test/expected/%s-%s.txt' % (self.name, cmd)
    def out_name(self, cmd):
        if Corpus.flat:
            return 'test/%s-%s-output.txt' % (self.name, cmd)
        else:
            return 'test/output/%s-%s.txt' % (self.name, cmd)
    def gold_name(self, cmd):
        if Corpus.flat:
            return 'test/%s-%s-gold.txt' % (self.name, cmd)
        else:
            return 'test/gold/%s-%s.txt' % (self.name, cmd)
    def save(self):
        if not Corpus.flat:
            ensure_dir_exists('expected')
        for blob in self.data['cmds']:
            if blob['cmd'] in self.unsaved:
                save_output(self.exp_name(blob['cmd']), blob['expect'])
        self.unsaved = set()
    def load(self):
        if self.loaded:
            return
        if self.infile:
            ins = load_input(self.infile)
        else:
            ins = {hash_line(''): [0, '']}
        self.hashes = list(ins.keys())
        self.hashes.sort(key = lambda x: ins[x][0])
        outs = []
        self.data = {
            'inputs': ins,
            'cmds': [],
            'count': len(ins)
        }
        for c in self.command_list:
            expfile = self.exp_name(c)
            outdata = load_output(self.out_name(c),
                                  should_sort_analyses=(c in self.sort))
            expdata = {}
            if os.path.isfile(expfile):
                expdata = load_output(expfile)
            else:
                if not Corpus.flat:
                    ensure_dir_exists('expected')
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
                'relevant': (c in self.relevant_commands),
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
    def page(self, start, page_len):
        hs = self.hashes[start:start+page_len]
        def hf(dct):
            nonlocal hs
            return {k:v for k, v in dct.items() if k in hs}
        return {
            'inputs': hf(self.data['inputs']),
            'cmds': [
                {
                    'cmd': blob['cmd'],
                    'opt': blob['opt'],
                    'relevant': blob['relevant'],
                    'output': hf(blob['output']),
                    'expect': hf(blob['expect']),
                    'gold': hf(blob['gold']),
                    'trace': hf(blob['trace'])
                }
                for blob in self.data['cmds']
            ],
            'count': page_len,
            'add': self.data['add'],
            'del': self.data['del']
        }
    def step(self, s):
        return self.data['cmds'][self.commands.get(s, -1)]
    def get_changed_hashes(self):
        norm = set()
        imp = set()
        for cmd in self.relevant_commands:
            blob = self.step(cmd)
            for hsh in self.data['inputs']:
                if hsh not in blob['expect']:
                    continue
                if blob['output'][hsh][1] == blob['expect'][hsh][1]:
                    continue
                if hsh in blob['gold']:
                    if blob['output'][hsh][1] in blob['gold'][hsh]:
                        continue
                norm.add(hsh)
                if blob['relevant']:
                    imp.add(hsh)
        imp_ret = sorted(imp, key = lambda x: self.data['inputs'][x][0])
        norm -= imp
        norm_ret = sorted(norm, key = lambda x: self.data['inputs'][x][0])
        return imp_ret + norm_ret
    def display_line(self, hsh, step=None):
        # TODO: colors, diffs
        def indent(s):
            print('  ' + s.replace('\n', '\n  '))
        blob = self.step(step)
        if hsh in self.data['inputs']:
            print('%s %s of %s' % (self.name, self.hashes.index(hsh)+1, len(self.hashes)))
            print('INPUT:')
            indent(self.data['inputs'][hsh][1])
        else:
            print(self.name)
            print('INPUT: [sentence deleted from input corpus]')
        if hsh in blob['expect']:
            print('EXPECTED OUTPUT:')
            indent(blob['expect'][hsh][1])
        else:
            print('EXPECTED OUTPUT: [sentence added since last run]')
        if hsh in blob['output']:
            print('ACTUAL OUTPUT:')
            indent(blob['output'][hsh][1])
        if hsh in blob['gold']:
            print('IDEAL OUTPUTS:')
            for g in blob['gold'][hsh]:
                indent(g)
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
                if d in blob['gold']:
                    del blob['gold'][d]
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
                if h not in blob['expect']:
                    continue
                if blob['expect'][h][1] != blob['output'][h][1]:
                    blob['expect'][h][1] = blob['output'][h][1]
                    changes.append(h)
                    self.unsaved.add(blob['cmd'])
            if blob['cmd'] == last_step:
                break
        self.save()
        return list(set(changes))
    def set_gold(self, hsh, vals, step=None):
        blob = self.step(step)
        blob['gold'][hsh] = vals
        if not Corpus.flat:
            ensure_dir_exists('gold')
        save_gold(self.gold_name(blob['cmd']), blob['gold'])

def load_corpora(names, static=False):
    if not os.path.isdir('test') or not os.path.isfile('test/tests.json'):
        if os.path.isdir('.git'):
            if not static and check_git():
                load_corpora(names)
                return
        print('Test corpora not found. Please create test/tests.json')
        print('as described at https://wiki.apertium.org/wiki/User:Popcorndude/Regression-Testing')
        sys.exit(1)
    with open('test/tests.json') as ts:
        pats = []
        if names:
            for n in names:
                pats.append(re.compile(n))
        else:
            pats.append(re.compile('.*'))
        try:
            blob = json.load(ts)
            for k in blob:
                if k == 'settings':
                    Corpus.flat = (blob[k].get('structure', 'flat') != 'nested')
                    continue
                for p in pats:
                    if p.search(k):
                        Corpus(k, blob[k])
                        break
        except json.JSONDecodeError as e:
            print('test/tests.json is not a valid JSON document. First error on line %s' % e.lineno)
            sys.exit(1)

def test_run(corpora):
    ls = corpora
    if '*' in corpora:
        ls = list(Corpus.all_corpora.keys())
    for name in ls:
        Corpus.all_corpora[name].run()
    return True, ''

def cb_load(page, step=25):
    changes = {
        'changed_final': [],
        'changed_any': [],
        'unchanged': []
    }
    state = {
        '_step': step,
        '_ordered': [],
        '_page': page
    }
    ct_min = page * step
    ct_max = (page + 1) * step
    ct = 0
    for name in sorted(Corpus.all_corpora.keys()):
        corpus = Corpus.all_corpora[name]
        corpus.load()
        ct_next = ct + len(corpus)
        if ct_next < ct_min or ct >= ct_max:
            state[name] = corpus.page(0, 0)
        elif ct < ct_min:
            start = ct_min - ct
            ln = min(ct_max, ct_next) - ct_min
            state[name] = corpus.page(start, ln)
        else: # ct >= ct_min
            ln = min(ct_max, ct_next) - ct
            state[name] = corpus.page(0, ln)
        ct = ct_next
    state['_count'] = ct
    state['_pages'] = math.ceil(ct/step)
    return {'state': state}

def compress(s):
    step = 2 << 17
    producer = zlib.compressobj(level=9, wbits=15)
    idx = 0
    while idx < len(s):
        yield producer.compress(s[idx:idx+step])
        idx += step
    yield producer.flush()

THE_CALLBACK_LOCK = threading.Lock()

class CallbackRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def __init__(self, request, client_address, server, directory=None,
                 page_size=25):
        self.page_size = page_size
        super().__init__(request, client_address, server, directory=directory)

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

    def send_json(self, status, blob):
        # based on https://github.com/PierreQuentel/httpcompressionserver/blob/master/httpcompressionserver.py (BSD license)
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        rstr = json.dumps(blob).encode('utf-8')
        self.send_header('Content-Encoding', 'deflate')
        if len(rstr) < (2 << 18):
            # don't bother chunking shorter messages
            dt = b''.join(compress(rstr))
            self.send_header('Content-Length', len(dt))
            self.end_headers()
            self.wfile.write(dt)
        else:
            self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()
            for data in compress(rstr):
                if data:
                    ln = hex(len(data))[2:].upper().encode('utf-8')
                    self.wfile.write(ln + b'\r\n' + data + b'\r\n')
            self.wfile.write(b'0\r\n\r\n')

    def do_callback(self, params):
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
        shutdown = False

        THE_CALLBACK_LOCK.acquire()

        # TODO: error checking
        if params['a'][0] == 'init':
            resp['folder'] = os.path.basename(os.getcwd())
            resp['corpora'] = list(sorted(Corpus.all_corpora.keys()))
        elif params['a'][0] == 'load':
            try:
                resp = cb_load(int(params['p'][0]), self.page_size)
            except InputFileDoesNotExist as e:
                resp = {'error': 'Input file %s expected but not found! Server exiting.' % e.args[0]}
                shutdown = True
            except InputFileIsEmpty as e:
                resp = {'error': 'Input file %s contained no data! Server exiting.' % e.args[0]}
                shutdown = True
        elif params['a'][0] == 'run':
            try:
                good, output = test_run(params.get('c', ['*']))
                resp['good'] = good
                resp['output'] = output
            except ErrorInPipeline as e:
                resp = {'error': 'Command `%s` crashed. Server exiting.' % e.args[0]}
                shutdown = True
        elif params['a'][0] == 'accept-nd':
            resp['c'] = params['c'][0]
            try:
                resp['hs'] = Corpus.all_corpora[resp['c']].accept_add_del()
            except KeyError:
                resp = {'error': "Must run regression tests for corpus '%s' before accepting additions (with `make test` or the button at the top of the page)." % params['c'][0]}
                status = HTTPStatus.PRECONDITION_FAILED
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

        self.send_json(status, resp)
        THE_CALLBACK_LOCK.release()
        if shutdown:
            if 'error' in resp:
                sys.exit(1)
            else:
                sys.exit(0)

class BigQueueServer(socketserver.ThreadingTCPServer):
    request_queue_size = 100

def start_server(port, page_size=25):
    d = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/')
    ensure_javascript(d)
    handle = partial(CallbackRequestHandler, directory=d, page_size=page_size)
    print('Starting server')
    print('Open http://localhost:%d in your browser' % port)
    with BigQueueServer(('', port), handle) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('')
            # the exception raised by sys.exit() gets caught by the
            # server, so we need to be a bit more drastic
            os._exit(0)

class RegtestShell(cmd.Cmd):
    prompt = '> '
    lines_todo = defaultdict(list) # { corpus_name : [ hash, hash, ... ] }
    lines_accepted = defaultdict(list)
    corpus_filter = None
    current_corpus = None
    current_hash = None
    end_step = None
    show_step = None
    def __init__(self):
        print('\nRunning regression tests for %s' % os.path.basename(os.getcwd()))
        print('Type `help` for a list of available commands.\n')
        print('Loading corpora...')
        for k in sorted(Corpus.all_corpora.keys()):
            self.load_corpus(k)
        self.next_hash()
        super().__init__()
    def load_corpus(self, name):
        corp = Corpus.all_corpora[name]
        corp.load()
        self.lines_todo[name] = []
        if corp.data['add'] or corp.data['del']:
            print('Corpus %s has %s added lines and %s deleted lines since last run' % (name, len(corp.data['add']), len(corp.data['del'])))
            if yes_no('Run test and save changes?'):
                corp.run()
                corp.load()
                corp.accept_add_del()
            else:
                self.lines_todo[name] = corp.data['add'] + corp.data['del']
        self.lines_todo[name] += corp.get_changed_hashes()
        # TODO: important hashes in all corpora before unimporant ones
        print('Corpus %s has %s lines to be examined.' % (name, len(self.lines_todo[name])))
    def next_hash(self, drop_prev=False):
        if drop_prev and self.current_corpus in self.lines_todo:
            if self.current_hash in self.lines_todo[self.current_corpus]:
                self.lines_todo[self.current_corpus].remove(self.current_hash)
                if not self.lines_todo[self.current_corpus]:
                    del self.lines_todo[self.current_corpus]
        drop = []
        for k, l in self.lines_todo.items():
            if len(l) == 0:
                drop.append(k)
        for k in drop:
            del self.lines_todo[k]
        if self.corpus_filter:
            self.current_corpus = self.corpus_filter
        elif not self.current_corpus and len(self.lines_todo) > 0:
            self.current_corpus = list(sorted(self.lines_todo.keys()))[0]
        if self.current_corpus not in self.lines_todo:
            self.current_hash = None
        else:
            self.current_hash = self.lines_todo[self.current_corpus][0]
            self.do_show('')
    def do_s(self, arg):
        'Synonym for `show`'
        self.do_show(arg)
    def do_show(self, arg):
        '''Display the selected step of the current line.
`show [step]`  - Display step `step` of the current line.
`show`         - Display the default step of the current line.
If the default display step has not been set, the final step
will be used. Invoking this command with an argument also sets
the default display step.'''
        if self.current_corpus and self.current_hash:
            corp = Corpus.all_corpora[self.current_corpus]
            if arg:
                self.show_step = arg
            corp.display_line(self.current_hash, self.show_step)
        elif self.corpus_filter and len(self.lines_todo) > 0:
            print('No changed lines match current filter')
            print("Use 'filter' to change filter or 'quit' to exit")
        else:
            print('No more changed lines')
            print("Use 'run' to update tests or 'quit' to exit")
    def complete_show(self, text, line, begidx, endidx):
        ret = []
        if self.current_corpus in Corpus.all_corpora:
            corp = Corpus.all_corpora[self.current_corpus]
            for cmd in corp.commands:
                if cmd.startswith(text):
                    ret.append(cmd)
        return ret
    def do_a(self, arg):
        'Synonym for `accept`'
        self.do_accept('')
    def do_accept(self, arg):
        '''Accept the outputs of the current line and replace the expected outputs.
If `upto` has been called, this will not affect steps after the limit.
Abbreviated form: `a`'''
        if self.current_corpus and self.current_hash:
            corp = Corpus.all_corpora[self.current_corpus]
            corp.accept([self.current_hash], self.end_step)
        self.next_hash(True)
    def do_k(self, arg):
        'Synonym for `skip`'
        self.do_skip('')
    def do_skip(self, arg):
        '''Move to the next changed line.
Abbreviated form: `k`'''
        self.next_hash(True)
    def do_ag(self, arg):
        'Synonym for `addgold`'
        self.do_addgold('')
    def do_addgold(self, arg):
        '''Add the output for the currently displayed step of the current line
to the list of ideal outputs for that line.
This command also runs `accept`.
Abbreviated form: `ag`'''
        if self.current_corpus and self.current_hash:
            corp = Corpus.all_corpora[self.current_corpus]
            blob = corp.step(self.show_step)
            out = blob['output'][self.current_hash][1]
            gold = blob['gold'].get(self.current_hash, [])
            corp.set_gold(self.current_hash, gold + [out], self.show_step)
            self.do_accept('')
        else:
            print('No input selected')
    def do_rg(self, arg):
        'Synonym for `replacegold`'
        self.do_replacegold('')
    def do_replacegold(self, arg):
        '''Remove the list of ideal outputs for the current step of the current
line and replace them with the current output.
This command also runs `accept`.
Abbreviated form: `rg`'''
        if self.current_corpus and self.current_hash:
            corp = Corpus.all_corpora[self.current_corpus]
            out = corp.step(self.show_step)['output'][self.current_hash][1]
            corp.set_gold(self.current_hash, [out], self.show_step)
            self.do_accept('')
        else:
            print('No input selected')
    def do_r(self, arg):
        'Synonym for `run`'
        self.do_run(arg)
    def do_run(self, corpus):
        '''Run tests and display results
`run`         - Run tests for all corpora.
`run [name]`  - Run tests only for corpus `name`.
Abbreviated form: `r`'''
        if corpus == '*' or corpus == '':
            for name, corp in Corpus.all_corpora.items():
                print('Running %s' % name)
                corp.run()
                self.load_corpus(name)
        else:
            for name in corpus.split():
                if name in Corpus.all_corpora:
                    print('Running %s' % name)
                    Corpus.all_corpora[name].run()
                    self.load_corpus(name)
                else:
                    print("Corpus '%s' does not exist" % name)
        self.next_hash()
    def complete_run(self, text, line, begidx, endidx):
        ls = []
        for c in Corpus.all_corpora:
            if c.startswith(text):
                ls.append(c)
        return ls
    def do_upto(self, arg):
        '''Disregard changes after a particular step.
When `accept` is run, no steps after the last value passed to `upto`
will be updated. Calling without arguments will select the final step.
If the default display step is after the new limit step, the default
display step will be set to the new limit step.'''
        if not arg:
            self.end_step = None
        else:
            self.end_step = arg
            if self.current_corpus:
                cmd = Corpus.all_corpora[self.current_corpus].commands
                if cmd.get(self.end_step, 0) > cmd.get(self.show_step, len(cmd)):
                    self.show_step = self.end_step
    def complete_upto(self, *args):
        return self.complete_show(*args)
    def do_q(self, arg):
        'Synonym for `quit`'
        return self.do_quit('')
    def do_quit(self, arg):
        '''Exit the program.
Abbreviated form: `q`'''
        return True
    def do_EOF(self, arg):
        'Synonym for `quit` provided so that CTRL-D will work as expected.'
        print('')
        return self.do_quit('')

def check_hash(corpus, hsh):
    expect = True # matches expectation or gold in all cases
    gold = True   # matches gold in all cases
                  # note: if gold not present, returns False
    for c in corpus.relevant_commands:
        data = corpus.step(c)
        out = data['output'].get(hsh, [0, ''])[1]
        exp = data['expect'].get(hsh, [0, ''])[1]
        gld = data['gold'].get(hsh, [])
        if out in gld:
            continue
        else:
            gold = False
            if out != exp:
                expect = False
    return expect, gold

def static_test(ignore_add=False, threshold=100, quiet=True):
    n = len(Corpus.all_corpora.items())
    changed = set()
    total_tests = 0
    total_passes = 0
    for i, (name, corp) in enumerate(Corpus.all_corpora.items(), 1):
        print('Corpus %s of %s: %s' % (i, n, name))
        if not corp.loaded:
            corp.run()
            corp.load()
        if corp.data['add']:
            print('  %s tests added since last run' % len(corp.data['add']))
            if not ignore_add:
                changed.add(name)
        if corp.data['del']:
            print('  %s tests removed since last run' % len(corp.data['del']))
            if not ignore_add:
                changed.add(name)
        total = 0
        same = 0
        gold = 0
        for hsh in corp.data['inputs']:
            if hsh in corp.data['add']:
                continue
            e, g = check_hash(corp, hsh)
            total += 1
            if e:
                same += 1
                if g:
                    gold += 1
        total_tests += total
        total_passes += same
        if total > 0:
            print('  %s/%s (%s%%) tests pass' % (same, total, round(100.0*same/total, 2)), end='')
            if same != total:
                changed.add(name)
        if same > 0:
            print(' (%s/%s (%s%%) match gold)' % (gold, same, round(100.0*gold/same, 2)))
        else:
            print('')
        print('')
    if changed:
        if quiet:
            print('There were changes! Run `apertium-regtest cli` to update tests.')
            print('Changed corpora: ' + ', '.join(sorted(changed)))
        else:
            print('There were changes!')
            print('The tests need to be updated.')
            ls = sorted(changed)
            print('The corpora that contain changes are:', ', '.join(ls))
            print('This can be done in a browser by running')
            print('')
            print('  apertium-regtest web')
            print('')
            print('or on the command line with')
            print('')
            print('  apertium-regtest cli')
            print('')
            print('A specific corpus can be edited with `-c`, for example')
            print('')
            print('  apertium-regtest -c %s web' % ls[0])
            print('')
    else:
        print('All tests pass.')
    return ((100.0 * total_passes) / total_tests) >= threshold

if __name__ == '__main__':
    load_modes()
    import argparse
    parser = argparse.ArgumentParser(
        prog='apertium-regtest',
        description='Run and update regression tests for Apertium data repositories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
apertium-regtest has 3 modes available:
  - 'test' runs all tests, printing a report and setting the exit code
           if any failed. This is primarily intended for 'make test' recipes.
  - 'web'  starts a local webserver so that tests can be interactively
           updated from the browser.
  - 'cli'  interactively updates tests from the terminal.
''')
    parser.add_argument('mode', choices=['test', 'web', 'cli'])

    ### GENERAL ARGUMENTS
    parser.add_argument('-a', '--accept', action='store_true',
                        help="automatically accept additions and deletions")
    parser.add_argument('-c', '--corpus', action='append',
                        help="only load corpora matching a regular expression (this option can be provided multiple times)")

    # TEST ARGUMENTS
    test_gp = parser.add_argument_group('test mode options')
    test_gp.add_argument('-i', '--ignore-add', action='store_true',
                         help="in test mode, don't count added or deleted lines as failing")
    default_min = 100
    if os.environ.get('AP_REGTEST_MIN','').isnumeric():
        default_min = int(os.environ['AP_REGTEST_MIN'])
    test_gp.add_argument('-t', '--threshold', type=int, default=default_min,
                         help="percentage of tests required to count as passing (default 100 or AP_REGTEST_MIN)")
    default_quiet = os.environ.get('AP_REGTEST_QUIET', 'no').lower() == 'yes'
    test_gp.add_argument('-q', '--quiet', action='store_true',
                         help="print minimal error message on test failure",
                         default=default_quiet)

    # WEB ARGUMENTS
    web_gp = parser.add_argument_group('web mode options')
    web_gp.add_argument('-p', '--port', type=int, default=3000,
                        help="in web mode, run the server on this port (default 3000)")
    web_gp.add_argument('-z', '--pagesize', type=int, default=250,
                        help="size of blocks to send to browser in web mode (default 250)")

    # CLI ARGUMENTS
    cli_gp = parser.add_argument_group('cli mode options')

    args = parser.parse_args()
    if args.accept:
        load_corpora(args.corpus, static=True)
        for name, corp in Corpus.all_corpora.items():
            try:
                corp.run()
                corp.load()
                corp.accept_add_del()
            except (InputFileDoesNotExist, InputFileIsEmpty, ErrorInPipeline):
                sys.exit(1)
    if args.mode == 'test':
        load_corpora(args.corpus, static=True)
        try:
            if not static_test(args.ignore_add, threshold=args.threshold,
                               quiet=args.quiet):
                sys.exit(1)
        except (InputFileDoesNotExist, InputFileIsEmpty, ErrorInPipeline):
            sys.exit(1)
    elif args.mode == 'web':
        load_corpora(args.corpus, static=False)
        start_server(args.port, args.pagesize)
    elif args.mode == 'cli':
        load_corpora(args.corpus, static=False)
        try:
            RegtestShell().cmdloop()
        except (InputFileDoesNotExist, InputFileIsEmpty, ErrorInPipeline):
            sys.exit(1)
    else:
        print("Unknown operation mode. Expected 'test', 'web', or 'cli'.")
        sys.exit(1)
