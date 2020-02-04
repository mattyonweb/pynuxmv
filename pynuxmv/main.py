import ast, sys, os, re
import contextlib
from collections import namedtuple
from typing import Dict, List, NewType, Tuple, Union, Any

LineNo   = NewType("LineNo", int)

While  = namedtuple("While",  ["test", "loc_test", "loc_last"])
If     = namedtuple("If",     ["test", "loc_test", "loc_last"])
IfElse = namedtuple("IfElse", ["test", "loc_test", "loc_last_if", "loc_last"])

Assign = namedtuple("Assign", ["loc", "expr"])

class MyVisitor(ast.NodeTransformer):
    def __init__(self):
        self.counter: LineNo = LineNo(0) #for line number
        self.VAR:   Dict[str, str]  = dict()
        self.INIT:  Dict[str, Any]  = dict()
        self.NEXTS: Dict[str, List[NextInfo]] = dict()
        self.FLOW:  List[FlowInfo] = list()
        self.INVARS: List[str]     = list()
        self.LTLS: List[str]       = list()
        
    def update_counter(self):
        self.counter += 1
        print(f"{self.counter} ", end="")
        
    def generic_visit(self, node) -> str:
        """ Identical to default one, except this `return`s """
        for _, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        return self.visit(item)
            elif isinstance(value, ast.AST):
                return self.visit(value)

        return "unknown"

        
    def visit_Name(self, node) -> str:
        return node.id

    
    def visit_Constant(self, node) -> Any:
        return node.value

    
    def visit_Module(self, node):
        for cmd in node.body:
            self.update_counter()
            self.visit(cmd)

            
    def visit_Assign(self, node):
        """ x = 0 """
        var_name = node.targets[0].id
        value    = self.visit(node.value)

        if var_name not in self.VAR:
            self.VAR[var_name] = "integer" #TODO
            self.INIT[var_name] = value
            self.NEXTS[var_name] = list()
        else:
            self.NEXTS[var_name].append(Assign(self.counter, value))
            
        print( f"{var_name} := {value}")

        
    def visit_AugAssign(self, node):
        var_name = node.target.id
        if not isinstance(node.op, ast.Add):
            raise Exception(f"{node.op} not implemented")
        op  = node.op
        val = self.visit(node.value)

        print(f"{var_name} += {val}")

        self.NEXTS[var_name].append(
            Assign(self.counter, f"{var_name} + {val}"))

        
    def visit_BinOp(self, node):
        ops = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
               ast.Mod: "mod", ast.FloorDiv: "/"
        }
        left  = self.visit(node.left)
        right = self.visit(node.right)

        assert type(node.op) in ops, f"BinOp {str(node.op)} not implemented"

        return f"{left} {ops[type(node.op)]} {right}"

        
    def visit_Compare(self, node) -> str:
        conv_str = {
            ast.Lt: "<", ast.Gt: ">", ast.LtE: "<=",
            ast.Eq: "=", ast.GtE: ">="
        }

        left  = self.visit(node.left)
        op    = conv_str[type(node.ops[0])]
        right = self.visit(node.comparators[0])
        
        print(f"{left} {op} {right}")
        return f"{left} {op} {right}"

    def visit_BoolOp(self, node):
        conv_str = {
            ast.Or : "|", ast.And: "&"
        }
        op = node.op
        arg1, arg2 = [self.visit(arg) for arg in node.values]

        return f"{arg1} {conv_str[type(op)]} {arg2}"
            
        
    def visit_While(self, node):
        print("While: ", end="")
        test = self.visit(node.test)
        
        start_line = self.counter

        for cmd in node.body:
            self.update_counter()
            print("\t", end="")
            self.visit(cmd)

        end_line = self.counter
        self.FLOW.append( While(test, start_line, end_line) )
        # ("while", test, start_line, end_line) )

        self.update_counter() #"spazio bianco" dopo lo while per gestire i salti

        
    def visit_If(self, node):
        print("If: ", end="")
        test = self.visit(node.test)

        start_line = self.counter

        # IF
        for cmd in node.body:
            self.update_counter()
            print("\t", end="")
            self.visit(cmd)

        last_of_if = self.counter
        self.update_counter()
        
        # ELSE (se c'è)
        if len(node.orelse) > 0:
            print("Else: ")
            
            for cmd in node.orelse:
                self.update_counter()
                print("\t", end="")
                self.visit(cmd)

            self.FLOW.append(
                IfElse(test, start_line, last_of_if, self.counter))
                # ("if-else", test, lineno, last_of_if, self.counter + 1) )

            self.update_counter()
            
        else:
            self.FLOW.append(
                If(test, start_line, last_of_if))
                # ("if-noelse", test, lineno, self.counter + 1) )

        # self.update_counter()
        

    def is_the_function(self, fname, node):
        try:
            if not node.value.func.id == fname:
                return False
        except AttributeError:
            return False
        return True
        
    def is_invarspec(self, node) -> Union[bool, str]:
        if self.is_the_function("invarspec", node):
            return node.value.args[0].value
        return False

    def is_ltlspec(self, node) -> Union[bool, str]:
        if self.is_the_function("ltlspec", node):
            return node.value.args[0].value
        return False
    
    def visit_Expr(self, node):
        if invar := self.is_invarspec(node):
            self.INVARS.append(invar)
        elif ltl := self.is_ltlspec(node):
            self.LTLS.append(ltl)
        else:
            self.generic_visit(node)

            
    def visit_ImportFrom(self, node):
        pass

    ###############################################
    
    def line_flow(self) -> str:
        out = "next(line) := case\n"
        
        for obj in self.FLOW:
            if isinstance(obj, While):
                out += f"\tline = {obj.loc_test} & {obj.test}: line + 1; -- while(True)\n"
                out += f"\tline = {obj.loc_test}:  {obj.loc_last + 2}; -- while(False)\n"
                out += f"\tline = {obj.loc_last+1}: {obj.loc_test}; -- loop while\n"
            elif isinstance(obj, If):                
                out += f"\tline = {obj.loc_test} & {obj.test}: line + 1; -- if(True)\n"
                out += f"\tline = {obj.loc_test}: {obj.loc_last + 2}; -- if(False)\n"
            elif isinstance(obj, IfElse): 
                out += f"\tline = {obj.loc_test} & {obj.test}: line + 1; -- if(True)\n"
                out += f"\tline = {obj.loc_last_if}: {obj.loc_last + 2}; -- end if(True) \n"
                out += f"\tline = {obj.loc_test}: {obj.loc_last_if + 2}; -- else\n"
                
        out += f"\tline = {self.counter}: {self.counter}; \n" 
        out += "\tTRUE: line + 1; \n"
        out += "esac;\n\n"

        return out
        
        

    def transpile(self) -> str:
        out = "MODULE main\n\n"

        out += "VAR\n"
        for k, v in self.VAR.items():
            out += f"{k}: {v};\n"
        out += "line: integer;\n"
        out += "\n"

        out += "ASSIGN\n"
        for k, v in self.INIT.items():
            out += f"init({k}) := {v};\n"
        out += "init(line) := 1;\n" #????? 0 o 1?
        out += "\n"
        
        out += self.line_flow()
        
        for var_name, l in self.NEXTS.items():
            sub_out = f"next({var_name}) := case\n"

            for update in l:
                sub_out += f"\tline = {update.loc}: {update.expr};\n"
                    
            sub_out += f"\tTRUE: {var_name}; \n"
            sub_out += "esac;\n\n"

            out += sub_out

        for invar in self.INVARS:
            out += f"INVARSPEC {invar};\n"
        for ltl in self.LTLS:
            out += f"LTLSPEC {ltl};\n"
        return out
    
######################################################

mv = MyVisitor()

# placeholders for specs declaration & co.
def invarspec(_: str):
    pass
def ltlspec(_: str):
    pass
def start_nuxmv():
    pass
def end_nuxmv():
    pass

ex = """
if a:
  
  start_nuxmv()
  dump(2, "lol")

  end_nuxmv()

print(1)
"""


@contextlib.contextmanager
def nostdout():
    """ Redirect stdout to /dev/null """
    save_stdout = sys.stdout
    sys.stdout = open(os.devnull, "w")
    yield
    sys.stdout = save_stdout
    

        
def run_single(code, fname_out="out.smv", quiet=True):
    """ Transpiles the given `code` and saves it to file. """ 
    mv = MyVisitor()

    def runner():
        mv.visit(ast.parse(code))
        open(fname_out, "w").write(mv.transpile())
        print()
        return mv

    if quiet:
        with nostdout():
            return runner()
    else:
        return runner()


    
def nuxmv_blocks(code):
    """ Given the `entire` source code, finds the blocks that are
    enclosed by `start_nuxmv()` and `end_nuxmv()`, if any. Then,
    returns these blocks. """
    regex  = re.compile(r"^\s*?start_nuxmv\(\).*?end_nuxmv\(\)", re.DOTALL | re.M)
    blocks = regex.findall(code)
    
    if len(blocks) == 0:
        return [] # no block found (aka. consider entire src code)

    # sanitize (remove harmful identation)
    out_blocks = list()
    for block in blocks:
        lines = [line for line in block.split("\n") if len(line) > 0]
        first_statement = lines[0]
        indent = len(first_statement) - len(first_statement.lstrip())
        lines = [line[indent:] for line in lines]

        out_blocks.append("\n".join(lines))

    return out_blocks

    
def run(code, fname_out="out.smv", quiet=True):
    results = list()
    found   = nuxmv_blocks(code)

    if len(found) == 0:
        return ([fname_out], [run_single(code, fname_out, quiet)])

    fnames_generated = list()
    for i, block in enumerate(found):
        fname_out__ = f"{fname_out}{i}"
        results.append(run_single(block, fname_out__, quiet))
        fnames_generated.append(fname_out__)

    return (fnames_generated, results)
        
# run(ex)

import astpretty
def pp(src):
    astpretty.pprint(ast.parse(src), show_offsets=False)

