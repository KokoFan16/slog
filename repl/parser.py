'''
A command parser written using ply

Kris Micinski
Yihao Sun
'''

import ply.lex as lex
import ply.yacc as yacc

from repl.commands import *

tokens = (
    'ID', 'LPAREN','RPAREN','STRING'
    )
# Tokens

t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_STRING  = r'".*?"'
t_ID    = r'[a-zA-Z0-9_]+'

# Ignored characters
t_ignore = " \t"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

# Build the lexer
lexer = lex.lex()

# Parsing rules

precedence = (
    # ('left','PLUS','MINUS'),
    # ('left','TIMES','DIVIDE'),
    # ('right','UMINUS'),
)

s = None

CMD = ['help', 'run', 'connect', 'dump', 'showdb', 'load', 'commit', 'compile']

def p_statement_unary(t):
    'statement : ID'
    unary_cmd = t[1].strip()
    if unary_cmd == 'help':
        t[0] = HelpCommand()
    elif unary_cmd == 'showdb':
        t[0] = ShowDbCommand()
    elif unary_cmd == 'commit':
        t[0] = NotImplCommand(unary_cmd)
    else:
        print(f"Unrecognized unary command {unary_cmd} syntax, please type `help`!")

def p_statement_id_cmd(t):
    'statement : ID ID'
    id_cmd = t[1]
    if id_cmd == "dump":
        t[0] = IdCommand(t[2])
    else:
        print("Unrecognized ID, please type `help`!")

def p_statement_str_cmd(t):
    'statement : ID STRING'
    str_arg = t[2][1:-1]
    # if t[1] == "run":
    #     t[0] = RunCommand(str)
    if t[1] == "connect":
        t[0] = ConnectCommand(str_arg)
    elif t[1] == "load":
        t[0] = LoadCommand(str_arg)
    elif t[1] == "compile":
        t[0] = CompileCommand(str_arg)
    else:
        print("Unrecognized str command syntax, please type `help`!")

def p_statement_str_id_cmd(t):
    'statement : ID STRING ID'
    if t[1] == "run":
        t[0] = RunWithDbCommand(t[2][1:-1], t[3].strip())

def p_error(t):
    if t:
        print("Unrecognized command at '%s'" % t.value)
    else:
        print("Unrecognized command syntax")

parser = yacc.yacc(debug=True,write_tables=True)

class CommandParser():
    def __init__(self):
        pass
    def parse(self, cmd):
        """ parsing command """
        return parser.parse(cmd)
