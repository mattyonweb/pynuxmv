import ast, re
import pynuxmv.optimizations as optm
from collections import namedtuple
from typing import Dict, List, Tuple, Union, Any

VarName  = str

While  = namedtuple("While",  ["test", "loc_test", "loc_last"])
If     = namedtuple("If",     ["test", "loc_test", "loc_last"])
IfElse = namedtuple("IfElse", ["test", "loc_test", "loc_last_if", "loc_last"])

Assign = namedtuple("Assign", ["loc", "expr"])



class MyVisitor(ast.NodeTransformer):
    def __init__(self, quiet=True, **kwargs):
        # current line number
        self.counter: int = 0
        # Types of the variables defined 
        self.TYPE:  Dict[VarName, str]  = dict()
        # Initial values of variables
        self.INIT:  Dict[VarName, str]  = dict()
        # Next states of a variable (comprises LOC info)
        self.NEXTS: Dict[VarName, List[Assign]] = dict()
        # Next state of the `line` variable
        self.FLOW:  List[FlowInfo] = list()
        
        # Conditions to test
        self.INVARS: List[str]     = list()
        self.POSTCONDS: List[str]  = list()
        self.LTLS: List[str]       = list()

        # Miscellaneus 
        self.quiet: bool   = quiet
        self.options: Dict = kwargs
        
        # If True, next call to `update_counter()` will not update the LOC counter
        # Very ugly and side-effect-ish
        self.__dont_update_line_counter = False

        
    def print(self, s, *args, **kwargs):
        if not self.quiet:
            print(s, *args, **kwargs)

            
    def update_counter(self):
        if self.__dont_update_line_counter:
            self.__dont_update_line_counter = False
            return
        self.counter += 1
        self.print(f"{self.counter} ", end="")
        
        
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
        base   = self.visit(node.value)
        slice_ = self.visit(node.slice.value)

        if isinstance(node.ctx, ast.Load):
            return f"READ({base}, {slice_})"
        else:
            return base
    
           
    def visit_Assign(self, node):
        # a, b = 1, 2
        if isinstance(node.targets[0], ast.Tuple):
            originals = [n for n in node.targets[0].elts]
            var_names = [n.id for n in node.targets[0].elts] #TODO self.visit()
            values    = [self.visit(n) for n in node.value.elts]
        else: # a = 2
            originals = [node.targets[0]]
            var_names = [self.visit(node.targets[0])] 
            values    = [self.visit(node.value)]

        for i, (var_name, value) in enumerate(zip(var_names, values)):

            #diocan
            if isinstance(originals[i], ast.Subscript):
                idx = self.visit(originals[i].slice.value)
                self.NEXTS[var_name].append(
                    Assign(self.counter, f"WRITE({var_name}, {idx}, {value})")
                )
                continue
            
            if var_name not in self.TYPE:
                self.TYPE[var_name] = "integer"
                self.INIT[var_name] = value
                self.NEXTS[var_name] = list()

                #optimization: reduces the final number of lines
                # ==> less states for nuxmv to examine
                self.__dont_update_line_counter = True 
            else:
                self.NEXTS[var_name].append(Assign(self.counter, value))

            self.print( f"{var_name} := {value}")
        return( f"{var_names} := {values}")
            

            
    
    def visit_AnnAssign(self, node):
        var_name = node.target.id
        value    = self.visit(node.value)
        type__   = self.visit(node.annotation)

        types = {
            "bool": "boolean", "int": "integer",
            "list": "array integer of integer"     
        }

        if type__ == "list":
            if var_name not in self.TYPE:
                self.TYPE[var_name]   = types[type__]
                self.NEXTS[var_name] = list()
            
            self.NEXTS[var_name].append(Assign(self.counter, value.format(var_name)))

        else:
            if var_name not in self.TYPE:
                self.TYPE[var_name] = types[type__]
                self.INIT[var_name] = value
                self.NEXTS[var_name] = list()
                self.__dont_update_line_counter = True
            else:
                self.NEXTS[var_name].append(Assign(self.counter, value))

        self.print( f"{var_name} := {value}")
        return f"{var_name} := {value}"

    
    
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
        
        self.print(f"{left} {op} {right}")
        return f"{left} {op} {right}"


    def visit_BoolOp(self, node):
        conv_str = {
            ast.Or : "|", ast.And: "&"
        }
        op = node.op
        # arg1, arg2 = [self.visit(arg) for arg in node.values]
        args = [self.visit(arg) for arg in node.values]

        out = f"{args[0]}"
        for arg in args[1:]:
            out += f" {conv_str[type(op)]} {arg}"
        return out

    
    
    def visit_While(self, node):
        self.print("While: ", end="")
        test = self.visit(node.test)


        start_line = self.counter

        for cmd in node.body:
            self.update_counter()
            self.print("\t", end="")
            self.visit(cmd)

        end_line = self.counter
        self.FLOW.append( While(test, start_line, end_line) )

        self.update_counter() #"spazio bianco" dopo lo while per gestire i salti
        
        
    
    def visit_If(self, node):
        test = self.visit(node.test)
        self.print(f"If {test}:\n")
        
        start_line = self.counter

        # IF
        for cmd in node.body:
            self.update_counter()
            self.print("\t", end="")
            self.visit(cmd)

        last_of_if = self.counter
        self.update_counter()
        
        # ELSE (se c'è)
        if len(node.orelse) > 0:
            self.print("Else: ")
            
            for cmd in node.orelse:
                self.update_counter()
                self.print("\t", end="")
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

    def is_postcondition(self, node) -> Union[bool, Tuple[str, bool]]:
        if self.is_the_function("postcondition", node):
            return (node.value.args[0].value, node.value.args[1].value)
        return False
    
    
    def visit_Expr(self, node):
        if invar := self.is_invarspec(node):
            self.INVARS.append(invar)
            self.__dont_update_line_counter = True
            
        elif ltl := self.is_ltlspec(node):
            self.LTLS.append(ltl)
            self.__dont_update_line_counter = True
            
        elif postcond_tupla := self.is_postcondition(node):
            postcond, strong = postcond_tupla
            if strong:
                strong_postc = "("
                for s in self.POSTCONDS[:-1]:
                    strong_postc += f"({s}) & "
                strong_postc += f"({self.POSTCONDS[-1]}) )"
                self.POSTCONDS.append(f"{strong_postc} -> (line = {self.counter} -> {postcond})")
            else:
                self.POSTCONDS.append(f"line = {self.counter} -> {postcond}")
            self.__dont_update_line_counter = True
            
        elif isinstance(node.value, ast.UnaryOp):
            assert isinstance(node.value.op, ast.USub), "not USub()!"
            return f"(- {self.visit(node.value.operand)})"
        else:
            return self.generic_visit(node)

        
    def visit_range(self, args: list):
        if len(args) == 1:
            return [0, self.visit(args[0]), 1], ast.Lt()
        elif len(args) == 2:
            return [self.visit(args[0]), self.visit(args[1]), 1], ast.Lt()
        else:
            # TODO!!!! Bug: non è che se ci sono tre argomenti il terzo
            # è necessariamente negativo!
            return [self.visit(arg) for arg in args], ast.Gt() 

            
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
        
        [a, b, s], comparison = self.visit_range(node.iter.args)

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
            self.print("\t", end="")
            self.visit(cmd)

        
    def visit_ImportFrom(self, node):
        self.__dont_update_line_counter = True

            
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
        for k, v in self.TYPE.items():
            out += f"{k}: {v};\n"

            
        if self.options.get("bounded_lineno", False): 
            out += "line: " + str(list(range(1, self.counter+1))).replace("[", "{").replace("]", "}") + ";\n"
        else:
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
        for postc in self.POSTCONDS:
            out += f"INVARSPEC {postc};\n"
        for ltl in self.LTLS:
            out += f"LTLSPEC {ltl};\n"
        return out
    
######################################################


# placeholders for specs declaration & co.
def invarspec(_: str):
    pass
def ltlspec(_: str):
    pass
def postcondition(_: str, strong: bool):
    pass
def start_nuxmv():
    pass
def end_nuxmv():
    pass

        
def run_single(code, fname_out="out.smv", quiet=True,
               optimizations: List[optm.Optimization]=None,
               **options):
    """ Transpiles the given `code` and saves it to file. """ 
    mv = MyVisitor(quiet=quiet, **options)

    def runner():
        ast_code = ast.parse(code)
        
        if not optimizations is None:
            for optTransformer in optimizations:
                ast_code = optTransformer.visit(ast_code)
                
        mv.visit(ast_code)
        open(fname_out, "w").write(mv.transpile())
        return mv

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


################################################################


def run(code, fname_out="out.smv", quiet=True,
        optimizations: List[optm.Optimization]=None,
        **options):
    results = list()
    found   = nuxmv_blocks(code)

    if len(found) == 0:
        return ([fname_out], [run_single(code, fname_out, quiet, optimizations, **options)])

    fnames_generated = list()
    for i, block in enumerate(found):
        fname_out__ = f"{fname_out}{i}"
        results.append(run_single(block, fname_out__, quiet, **options))
        fnames_generated.append(fname_out__)

    return (fnames_generated, results)


def pp(src: str):
    """ Pretty print of AST """
    try:
        import astpretty
        astpretty.pprint(ast.parse(src), show_offsets=False)
    except ImportError:
        print("Warning: couldn't find module 'astpretty'; falling back to ast.dump()")
        ast.dump(ast.parse(src))


def tocode(ast_):
    """ From AST to string of code """
    try:
        import astor
        return astor.to_source(ast_)
    except ImportError:
        print("Warning: couldn't find module 'astor'; nothing will be done")


ex = """
from pynuxmv.main import *

x = 0
y = 1
l: list = [1,2,3]
while (y < 10):
  x += 1
  y += 1
  y += 0
  l[2] = l[2] + x 

postcondition("y = 10", False)
postcondition("x = 9", False)
postcondition("l[2] = 48", True)
"""
