import ast, sys, os, re
import pynuxmv.optimizations as optm
from collections import namedtuple
from typing import Dict, List, NewType, Tuple, Union, Any

LineNo   = NewType("LineNo", int)

While  = namedtuple("While",  ["test", "loc_test", "loc_last"])
If     = namedtuple("If",     ["test", "loc_test", "loc_last"])
IfElse = namedtuple("IfElse", ["test", "loc_test", "loc_last_if", "loc_last"])

Assign = namedtuple("Assign", ["loc", "expr"])

from functools import wraps


class MyVisitor(ast.NodeTransformer):
    def __init__(self, quiet=True):
        self.counter: LineNo = LineNo(0) #for line number
        self.VAR:   Dict[str, str]  = dict()
        self.INIT:  Dict[str, Any]  = dict()
        self.NEXTS: Dict[str, List[NextInfo]] = dict()
        self.FLOW:  List[FlowInfo] = list()
        self.INVARS: List[str]     = list()
        self.LTLS: List[str]       = list()

        self.quiet: bool = quiet
        self.debug: List[str] = list()
        self.__dont_update_line_counter = False
        
    def debug_decorator(foo):
        def inner(*args):
            self = args[0]
            res = foo(*args)
            if res is None:
                self.debug.append( (self.counter, " "))
                if not self.quiet:
                    print(f"{self.counter}\t ")
            else:
                self.debug.append( (self.counter, res) )
                if not self.quiet:
                    print(f"{self.counter}\t{res} ")
            return res
        return inner
        
    def update_counter(self):
        if self.__dont_update_line_counter:
            self.__dont_update_line_counter = False
            return
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
        if node.value in [True, False]:
            return str(node.value).upper()
        return node.value

    def visit_Module(self, node):
        for cmd in node.body:
            self.update_counter()
            self.visit(cmd)


    def visit_List(self, node):
        template = "WRITE({}, {}, {})"
        out      = template
        
        for i, el in enumerate(node.elts[:-1]):
            visited_el = self.visit(el)
            out = out.format(template, i, visited_el)

        return out.format("{}", i+1, self.visit(node.elts[-1]))

    def visit_Subscript(self, node):
        base = self.visit(node.value)
        slice_ = self.visit(node.slice.value)

        if isinstance(node.ctx, ast.Load):
            return f"READ({base}, {slice_})"
        else:
            return base
    
    @debug_decorator        
    def visit_Assign(self, node):
        # a, b = 1, 2
        if isinstance(node.targets[0], ast.Tuple):
            originals = [n for n in node.targets[0].elts]
            var_names = [n.id for n in node.targets[0].elts] #TODO self.visit()
            values    = [self.visit(n) for n in node.value.elts]
        else: # a = 2
            originals = [node.targets[0]]
            var_names = [self.visit(node.targets[0])] #.id]
            values    = [self.visit(node.value)]

        for i, (var_name, value) in enumerate(zip(var_names, values)):

            #diocan
            if isinstance(originals[i], ast.Subscript):
                idx = self.visit(originals[i].slice.value)
                self.NEXTS[var_name].append(
                    Assign(self.counter, f"WRITE({var_name}, {idx}, {value})")
                )
                continue
            
            if var_name not in self.VAR:
                self.VAR[var_name] = "integer"
                self.INIT[var_name] = value
                self.NEXTS[var_name] = list()

                #optimization: reduces the final number of lines
                # ==> less states for nuxmv to examine
                self.__dont_update_line_counter = True 
            else:
                self.NEXTS[var_name].append(Assign(self.counter, value))

            print( f"{var_name} := {value}")
        return( f"{var_names} := {values}")
            

            
    @debug_decorator
    def visit_AnnAssign(self, node):
        var_name = node.target.id
        value    = self.visit(node.value)
        type__   = self.visit(node.annotation)

        types = {
            "bool": "boolean", "int": "integer",
            "list": "array integer of integer"     
        }

        if type__ == "list":
            if var_name not in self.VAR:
                self.VAR[var_name]   = types[type__]
                self.NEXTS[var_name] = list()
            
            self.NEXTS[var_name].append(Assign(self.counter, value.format(var_name)))

        else:
            if var_name not in self.VAR:
                self.VAR[var_name] = types[type__]
                self.INIT[var_name] = value
                self.NEXTS[var_name] = list()
                self.__dont_update_line_counter = True
            else:
                self.NEXTS[var_name].append(Assign(self.counter, value))

        print( f"{var_name} := {value}")
        return f"{var_name} := {value}"

    
    @debug_decorator
    def visit_AugAssign(self, node):
        """ x *= y is the same as x = x * y """
        variable_store = node.target
        variable_load  = node.target
        variable_load.ctx = ast.Load()
        return self.visit(
            ast.Assign(
                targets=[variable_store],
                value=ast.BinOp(
                    left=variable_load,
                    op=node.op,
                    right=node.value,
                ),
                type_comment=None,
            )
        )

        
    def visit_BinOp(self, node):
        ops = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
               ast.Mod: "mod", ast.FloorDiv: "/" }
        
        left  = self.visit(node.left)
        right = self.visit(node.right)

        assert type(node.op) in ops, f"BinOp {str(node.op)} not implemented"

        return f"{left} {ops[type(node.op)]} {right}"

    
    def visit_UnaryOp(self, node):
        conv_str = {
            ast.UAdd: "+", ast.USub: "-", ast.Not: "!"
        }
        
        return f"({conv_str[type(node.op)]} {self.visit(node.operand)})"

    
    def visit_Compare(self, node) -> str:
        conv_str = {
            ast.Lt: "<", ast.Gt: ">", ast.LtE: "<=",
            ast.Eq: "=", ast.GtE: ">=", ast.NotEq: "!="
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

    
    @debug_decorator
    def visit_While(self, node):
        print("While: ", end="")
        test = self.visit(node.test)
        self.debug.append( (self.counter, f"While {test}") )


        start_line = self.counter

        for cmd in node.body:
            self.update_counter()
            print("\t", end="")
            self.visit(cmd)

        end_line = self.counter
        self.FLOW.append( While(test, start_line, end_line) )

        self.update_counter() #"spazio bianco" dopo lo while per gestire i salti
        
        
    @debug_decorator
    def visit_If(self, node):
        test = self.visit(node.test)
        print(f"If {test}:\n")
        self.debug.append( (self.counter, f"If {test}") )
        
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
            self.debug.append( (self.counter, f"Else") )
            
            for cmd in node.orelse:
                self.update_counter()
                print("\t", end="")
                self.visit(cmd)

            self.FLOW.append(
                IfElse(test, start_line, last_of_if, self.counter))

            self.update_counter()
            
        else:
            self.FLOW.append(
                If(test, start_line, last_of_if))

        

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

    @debug_decorator
    def visit_Expr(self, node):
        if invar := self.is_invarspec(node):
            self.INVARS.append(invar)
            self.__dont_update_line_counter = True
        elif ltl := self.is_ltlspec(node):
            self.LTLS.append(ltl)
            self.__dont_update_line_counter = True
        elif isinstance(node.value, ast.UnaryOp):
            assert isinstance(node.value.op, ast.USub), "not USub()!"
            return f"(- {self.visit(node.value.operand)})"
        else:
            return self.generic_visit(node)

    @debug_decorator
    def visit_For(self, node):
        """  for x in range(a, b, c)

        is equal to:

             x := a
             while (x < b): #x > b in case c < 0
               ...
               x += c
        """
        var_name = node.target.id
        
        assert node.iter.func.id == "range", "for doesn't use range()"
        range_args = node.iter.args
        if len(range_args) == 1:
            a, b, s = 0, self.visit(range_args[0]), 1
            comparison = ast.Lt()
        elif len(range_args) == 2:
            a, b, s = self.visit(range_args[0]), self.visit(range_args[1]), 1
            comparison = ast.Lt()
        else:
            print(range_args[2])
            a, b, s = self.visit(range_args[0]), self.visit(range_args[1]), self.visit(range_args[2])
            comparison = ast.Gt()

        increment_ast = ast.AugAssign(
            target=ast.Name(id=var_name, ctx=ast.Store()),
            op=ast.Add(),
            value=ast.Constant(value=s, kind=None),
        )
        
        while_translation = [
            ast.Assign(
                targets=[ast.Name(id=var_name, ctx=ast.Store())],
                value=ast.Constant(value=a, kind=None),
                type_comment=None,
            ),
            ast.While(
                test=ast.Compare(
                    left=ast.Name(id=var_name, ctx=ast.Load()),
                    ops=[comparison],
                    comparators=[ast.Constant(value=b, kind=None)],
                ),
                body=node.body + [increment_ast],
                orelse=[],
            ),
        ]

        for cmd in while_translation:
            self.update_counter()
            print("\t", end="")
            self.visit(cmd)

        
    def visit_ImportFrom(self, node):
        pass

    def debug_dump(self):
        for k, v in self.debug:
            print(k, "\t", v)
            
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
            
        # out += "line: " + str(list(range(1, self.counter+1))).replace("[", "{").replace("]", "}") + ";\n"
        out += "line: integer;\n"
        out += "\n"

        out += "ASSIGN\n"
        for k, v in self.INIT.items():
            out += f"init({k}) := {v};\n"
        out += "init(line) := 1;\n" #????? 0 o 1?
        out += "\n"
        
        out += self.line_flow()
        
        for var_name, l in self.NEXTS.items():
            if l == []: #if a variable never get changed
                out += f"next({var_name}) := {var_name};\n\n"
                continue
            
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


# placeholders for specs declaration & co.
def invarspec(_: str):
    pass
def ltlspec(_: str):
    pass
def start_nuxmv():
    pass
def end_nuxmv():
    pass

import contextlib
@contextlib.contextmanager
def nostdout():
    """ Redirect stdout to /dev/null """
    save_stdout = sys.stdout
    sys.stdout = open(os.devnull, "w")
    yield
    sys.stdout = save_stdout
    

        
def run_single(code, fname_out="out.smv", quiet=True,
               optimizations: List[optm.Optimization]=None):
    """ Transpiles the given `code` and saves it to file. """ 
    mv = MyVisitor()

    def runner():
        ast_code = ast.parse(code)
        
        if not optimizations is None:
            for optTransformer in optimizations:
                ast_code = optTransformer.visit(ast_code)
                
        mv.visit(ast_code)
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

    
def run(code, fname_out="out.smv", quiet=True,
        optimizations: List[optm.Optimization]=None):
    results = list()
    found   = nuxmv_blocks(code)

    if len(found) == 0:
        return ([fname_out], [run_single(code, fname_out, quiet, optimizations)])

    fnames_generated = list()
    for i, block in enumerate(found):
        fname_out__ = f"{fname_out}{i}"
        results.append(run_single(block, fname_out__, quiet))
        fnames_generated.append(fname_out__)

    return (fnames_generated, results)

def pp(src):
    try:
        import astpretty
        astpretty.pprint(ast.parse(src), show_offsets=False)
    except ImportError:
        print("Warning: couldn't find module 'astpretty'; falling back to ast.dump()")
        ast.dump(ast.parse(src))
    
def tocode(ast_):
    try:
        import astor
        return astor.to_source(ast_)
    except ImportError:
        print("Warning: couldn't find module 'astor'; nothing will be done")



ex = """
x = 0
y = 1
l: list = [1,2,3]
while (y < 10):
  x += 1
  y += 1
  l[2] = l[2] + 1

#ltlspec("F y = 10")
#ltlspec("F x = 9")
ltlspec("x = 9 -> F READ(l, 2) = 12")
"""
