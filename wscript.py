#! /usr/bin/env python
import os
'''
https://waf.io/apidocs/tutorial.html
python3 waf configure
'''
TO_DEBUG = False


def log(msg):
    if TO_DEBUG:
        print(msg)


class Node():
    def __init__(self, name):
        self.fullpath = name
        self._name = name
        self._text = None

        if '/' in name:
            names = self._name.split('/')
            self._name = names[len(names) - 1]

    @property
    def name(self):
        return self

    @property
    def text(self):
        log(['self.fullpath', self.fullpath])

        if not os.path.isfile(self.fullpath):
            return

        with open(self.fullpath, 'r') as file:
            text = file.read()  # .replace('\n', '').replace('*/', '*/;')  # .replace("\'", "'")  # .replace('\t', ' ')
            return text

    @text.setter
    def text(self, x):
        if x:
            self.to_file(x)

    @text.deleter
    def text(self):
        del self._text

    def to_file(self, data):
        if not os.path.isfile(self.fullpath):
            return

        with open(self.fullpath, "w") as f:
            f.truncate(0)
            f.write(data)
            f.close()

    def __sub__(self, b):
        return Node(self.fullpath.rstrip(b))

    def __add__(self, b):
        n = Node(self.fullpath + str(b))
        return n

    def __str__(self):
        return self._name


def configure(context):
    if not hasattr(context, 'Node'):
        context.Node = Node

    minifyfiles(context)


class Context():
    def Node(self, f):
        return Node(f)


def minifyfiles(context):
    src = context.Node('src/jSignature.js')

    distfolder = context.Node('libs/')
    pluginsfolder = context.Node('src/plugins/')

    # Compressing jSignature + some plugins into one mini
    minified = distfolder + src.name - '.js' + '.min.js'
    log("=== Compressing " + str(src.name) + " into " + minified.fullpath)
    minified.text = compress_with_closure_compiler(
        " ".join([
            src.text.replace(
                "${buildDate}", timeUTC()
            ).replace(
                "${commitID}", getCommitIDstring()
            ),
            (pluginsfolder + 'jSignature.UndoButton.js').text,
            # context.Node('plugins/signhere/jSignature.SignHere.js').text + \
            (pluginsfolder + 'jSignature.CompressorBase30.js').text,
            (pluginsfolder + 'jSignature.CompressorSVG.js').text
        ]))

    # wrapping that mini into "jQuery.NoConflict" prefix + suffix
    # and hosting it as separate mini
    (minified - '.js' + '.noconflict.js').text = ";(function($){\n" + minified.text + "\n})(jQuery);"


def timeUTC():
    import datetime
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M")


def getCommitIDstring():
    import subprocess
    if not subprocess.check_output:
        # let's not bother emulating it. Not important
        return ""
    else:
        return "commit ID " + str(
            subprocess.check_output([
                'git'
                , 'rev-parse'
                , 'HEAD'
            ]
        ).strip())


def compress_with_closure_compiler(code, compression_level = None):
    '''Sends text of JavaScript code to Google's Closure Compiler API
    Returns text of compressed code.
    '''
    log(['code', code])
    # script (with some modifications) from 
    # https://developers.google.com/closure/compiler/docs/api-tutorial1

    from http import client as httplib

    import urllib

    compression_levels = [
        'WHITESPACE_ONLY'
        , 'SIMPLE_OPTIMIZATIONS'
        , 'ADVANCED_OPTIMIZATIONS'
    ]

    if compression_level not in compression_levels:
        compression_level = compression_levels[1] # simple optimizations

    # Define the parameters for the POST request and encode them in
    # a URL-safe format.
    params = urllib.parse.urlencode([
        ('js_code', code)
        , ('compilation_level', compression_level)
        , ('output_format', 'json')
        , ('output_info', 'compiled_code')
        , ('output_info', 'warnings')
        , ('output_info', 'errors')
        , ('output_info', 'statistics')
        # , ('output_file_name', 'default.js')
        # , ('js_externs', 'javascript with externs') # only used on Advanced. 
      ])

    # Always use the following value for the Content-type header.
    headers = {"Content-type": "application/x-www-form-urlencoded"}
    conn = httplib.HTTPSConnection('closure-compiler.appspot.com')
    conn.request('POST', '/compile', params, headers)
    response = conn.getresponse()

    if response.status != 200:
        raise Exception("Compilation server responded with non-OK status of " + str(response.status))

    compressedcode = response.read()
    conn.close()

    import json  # needs python 2.6+ or simplejson module for earlier
    parts = json.loads(compressedcode)

    if 'errors' in parts:
        prettyerrors = ['\nCompilation Error:']
        for error in parts['errors']:
            prettyerrors.append(
                "\nln %s, ch %s, '%s' - %s" % (
                    error['lineno']
                    , error['charno']
                    , error['line']
                    , error['error']
                )
            )
        raise Exception(''.join(prettyerrors))

    log(["parts", parts])
    log(["parts['statistics']", parts['statistics']])

    return parts['compiledCode']


if __name__ == '__main__':
    context = Context()
    configure(context)
    # print("This is a Wak build automation tool script. Please, get Wak on GitHub and run it against the folder containing this automation script.")
    print('Done')
