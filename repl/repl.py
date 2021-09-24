'''
slog REPL entrance

Kris Micinski
Yihao Sun
'''

import copy
import grpc
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter, NestedCompleter, PathCompleter
from prompt_toolkit.completion.base import Completer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
import time
import timeit
from yaspin import yaspin
from repl.parser import *

# Generated protobufs stuff
import protobufs.slog_pb2 as slog_pb2
import protobufs.slog_pb2_grpc as slog_pb2_grpc

# How often to wait between pinging the server
PING_INTERVAL = .1

# Constants (see server.py)
STATUS_PENDING  = 0
STATUS_FAILED   = 1
STATUS_RESOLVED = 2
STATUS_NOSUCHPROMISE = -1

BANNER = '''
                   _____  __           
                  / ___/ / /___  ____ _
                  \__ \ / / __ \/ __ `/
                 ___/ / / /_/  / /_/ / 
                /____/_/\____/ \__, /  
                              /____/   
    A Parallel Datalog Engine!    
    Type `help` to see help information. 

'''

class StringPathCompeleter(Completer):
     def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        # stripped_len = len(document.text_before_cursor) - len(text)
        if "\"" in text:
            remain_document = Document(
                text[1:],
                cursor_position=document.cursor_position - 1
            )
            for c in PathCompleter().get_completions(remain_document, complete_event):
                yield c

def get_arity_souffle_facts(souffle_fpath):
    ''' get arity of a souffle facts file'''
    with open(souffle_fpath, 'r') as souffle_f:
        fst_line = souffle_f.readline()
    if fst_line.strip() == '':
        return -1
    else:
        return len(fst_line.strip().split('\t'))


def get_rel_name_souffle_fact(souffle_fpath):
    ''' get relation name from a souffle facts file '''
    return souffle_fpath.split('/')[-1][:-6]

class Repl:
    def __init__(self):
        print(BANNER)
        self._channel = None
        self._parser = CommandParser()
        self.reconnect("localhost")
        self.lasterr = None
        self.relations = []
        self.unroll_depth = 3

    def connected(self):
        return self._channel != None
    
    def reconnect(self,server):
        self._server = server
        self._channel = grpc.insecure_channel('{}:5108'.format(server))
        self._stub = slog_pb2_grpc.CommandServiceStub(self._channel)
        self._cur_time = -1
        # Hash from timestamps to database hashes
        self._times    = {}
    
    def upload_csv(self, csv_dir):
        ''' upload csv using tsv_bin tool '''
        csv_file_paths = []
        if os.path.isdir(csv_dir):
            for fname in os.listdir(csv_dir):
                if not fname.endswith('.facts'):
                    continue
                csv_file_paths.append(f'{csv_dir}/{fname}')
        elif csv_dir.strip().endswith('.facts'):
            csv_file_paths.append(csv_dir)
        if csv_file_paths == []:
            print("no valid facts file found! NOTICE: all csv facts file must has extension `.facts`")
            return
        for csv_fname in csv_file_paths:
            rel_name = get_rel_name_souffle_fact(csv_fname)
            with yaspin(text='uploading csv facts ...'):
                req = slog_pb2.PutCSVFactsRequest()
                req.relation_name = rel_name
                with open(csv_fname, 'r') as csv_f:
                    req.bodies.extend(csv_f.read())


    def run(self,filename):
        path = os.path.join(os.getcwd(),filename)
        elaborator = Elaborator()
        try:
            elaborator.elaborate(path)
        except FileNotFoundError as e:
            print("Error processing preambles:")
            print(e)
            return
        # Exchange hashes
        req = slog_pb2.HashesRequest()
        req.session_key = "empty"
        req.hashes.extend(elaborator.hashes.keys())
        response = self._stub.ExchangeHashes(req)
        req = slog_pb2.PutHashesRequest()
        req.session_key = "empty"
        for hsh in response.hashes:
            req.bodies.extend([elaborator.hashes[hsh]])
        response = self._stub.PutHashes(req)

        # Generate a compile request
        req = slog_pb2.CompileHashesRequest()
        req.buckets = 4096
        req.using_database = ""
        req.hashes.extend(elaborator.hashes.keys())
        response = self._stub.CompileHashes(req)
        cmmt = None
        initial_db = ""

        # Wait to resolve the promise in the terminal...
        with yaspin(text="Compiling...") as spinner:
            # Break when promise is resolved
            while True:
                time.sleep(PING_INTERVAL)
                p = slog_pb2.Promise()
                p.promise_id = response.promise_id
                res = self._stub.QueryPromise(p)
                if (cmmt == None and res.err_or_db != ""):
                    cmmt = res.err_or_db
                    spinner.write("✔ {}".format(cmmt))
                elif (cmmt != res.err_or_db):
                    cmmt = res.err_or_db
                    spinner.write("✔ {}".format(cmmt))
                elif (res.status == STATUS_PENDING):
                    continue
                elif (res.status == STATUS_FAILED):
                    spinner.fail("💥")
                    print("Compilation failed!")
                    print(res.err_or_db)
                    return
                elif (res.status == STATUS_RESOLVED):
                    spinner.ok("✅ ")
                    initial_db = res.err_or_db
                    break
        
        req = slog_pb2.RunProgramRequest()
        req.using_database = initial_db
        req.hashes.extend(elaborator.hashes.keys())

        # Get a promise for the running response
        response = self._stub.RunHashes(req)
        
        with yaspin(text="Running...") as spinner:
            while True:
                time.sleep(PING_INTERVAL)
                p = slog_pb2.Promise()
                p.promise_id = response.promise_id
                res = self._stub.QueryPromise(p)
                if (cmmt == None and res.err_or_db != ""):
                    cmmt = res.err_or_db
                    spinner.write("✔ {}".format(cmmt))
                elif (cmmt != res.err_or_db):
                    cmmt = res.err_or_db
                    spinner.write("✔ {}".format(cmmt))
                if (res.status == STATUS_PENDING):
                    continue
                elif (res.status == STATUS_FAILED):
                    spinner.fail("💥")
                    print("Execution failed!")
                    return
                elif (res.status == STATUS_RESOLVED):
                    spinner.ok("✅ ")
                    self.switchto_db(res.err_or_db)
                    return

    def switchto_db(self,db_id):
        self._cur_time += 1
        self._cur_db = db_id
        new_ts = self._cur_time
        self._times[new_ts] = db_id
        self.load_relations(db_id)
        self.tuples = {}

    def load_relations(self,db_id):
        req = slog_pb2.DatabaseRequest()
        req.database_id = db_id
        res = self._stub.GetRelations(req)
        self.relations = []
        for relation in res.relations:
            self.relations.append([relation.name,relation.arity,relation.tag])

    def lookup_rels(self,name):
        data = []
        for r in self.relations:
            if r[0] == name:
                data.append([r[1],r[2]])
        return data

    def fetch_tuples(self,name):
        print(name)
        req = slog_pb2.RelationRequest()
        print(req)
        req.database_id = self._cur_db
        arity   = self.lookup_rels(name)[0][0]
        req.tag = self.lookup_rels(name)[0][1]
        res = self._stub.GetTuples(req)
        n = 0
        x = 0
        tuples = []
        buf = [None] * (arity+1)
        for response in res:
            if (response.num_tuples == 0): continue
            for u64 in response.data:
                buf[x] = u64
                x += 1
                if (x == arity+1):
                    tuples.append(copy.copy(buf))
                    x = 0
                    n += 1
            assert (n == response.num_tuples)
        self.tuples[name] = tuples
        return tuples

    def recursive_dump_tuples(self,name):
        for tuple in self.fetch_tuples(name):
            print("\t".join(map(lambda x: str(x), tuple)))

    def pretty_dump_relation(self,name):
        if (len(self.lookup_rels(name)) == 0):
            print("No relation named {} in the current database".format(name))
            return
        elif (len(self.lookup_rels(name)) > 1):
            print("More than one arity for {}, not currently supporting printing for multi-arity relations".format(name))
            return
        self.recursive_dump_tuples(name)

    def get_front(self):
        if (not self.connected()):
            return "Disconnected"
        elif (self._cur_time == -1):
            return "⊥"
        else:
            return "t{}".format(self._cur_time)

    def loop(self):
        while True:
            try:
                front = self.get_front()
                relation_names = map(lambda x: x[0], self.relations)
                # completer = WordCompleter(relation_names)
                completer_map = {cmd: None for cmd in CMD}
                completer_map['dump'] = WordCompleter(relation_names)
                completer_map['run'] = StringPathCompeleter()
                completer_map['csv'] = StringPathCompeleter()
                completer = NestedCompleter(completer_map)
                text = prompt('σλoγ [{}] » '.format(front), bottom_toolbar=self.bottom_toolbar(), completer=completer)
                cmd = self._parser.parse(text)
                if cmd:
                    cmd.execute(self)
                else:
                    print("unrecognized command (try `help` once someone implements it)")
                    pass
            except EOFError:
                self.exit()
            except AssertionError:
                return
            
    def exit(self):
        print('Goodbye.')
        exit(0)

    def calc_ping(self):
        req = slog_pb2.PingRequest()
        start_time = timeit.default_timer()
        res = self._stub.Ping(req)
        end_time = timeit.default_timer()
        elapsed = end_time - start_time
        return elapsed * 1000

    def bottom_toolbar(self):
        ping = self.calc_ping()
        if self.connected():
            return HTML('<style color="lightgreen">[host: <b>{}</b> ping: {:.2f} ms]  [?? jobs in queue]</style>'.format(self._server,self.calc_ping()))
        else:
            return HTML('Disconnected. Use `connect <host>`')

repl = Repl()

try:
    while True:
        repl.loop()
except KeyboardInterrupt:
    repl.exit()
