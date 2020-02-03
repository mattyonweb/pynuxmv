import z3
import dis
import ast
import inspect as ins
import operator


class MyVisitor(ast.NodeTransformer):
    def __init__(self):
        self.counter = 0
        self.VAR   = dict()
        self.INIT  = dict()
        self.NEXTS = dict()
        self.FLOW  = list()
        self.INVARS = list()
        
    def update_counter(self):
        self.counter += 1
        print(f"{self.counter} ", end="")
        
    def generic_visit(self, node):
        """ Identical to default one, except this `return`s """
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        return self.visit(item)
            elif isinstance(value, ast.AST):
                return self.visit(value)
        else:
            return "unknown"

        
    def visit_Name(self, node):
        return node.id

    
    def visit_Constant(self, node):
        return node.value

    
    def visit_Module(self, node):
        for i, cmd in enumerate(node.body):
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
            
        print( f"Assign {var_name} := {value}")

        
    def visit_AugAssign(self, node):
        var_name = node.target.id
        if not isinstance(node.op, ast.Add):
            raise Exception(f"{node.op} not implemented")
        op  = node.op
        val = self.visit(node.value)

        print(f"{var_name} += {val}")

        self.NEXTS[var_name].append(
            ("increment", self.counter, f"{var_name} + {val}"))

        
    def visit_Compare(self, node):
        conv_str = {ast.Lt: "<", ast.Gt: ">"}
        conv_foo = {ast.Lt: operator.lt, ast.Gt: operator.gt}
        
        assert isinstance(node.left, ast.Name), "test non su variabile"

        left  = self.visit(node.left)
        op    = conv_str[type(node.ops[0])]
        right = self.visit(node.comparators[0])
        
        print(f"{left} {op} {right}")
        return f"{left} {op} {right}"
        
        
    def visit_While(self, node):
        print("While: ", end="")
        test = self.visit(node.test)
        
        start_line = self.counter

        for cmd in node.body:
            self.update_counter()
            print("\t", end="")
            self.visit(cmd)

        end_line = self.counter
        
        self.FLOW.append( ("while", test, start_line, end_line) )

    
    def is_invarspec(self, node):
        try:
            node.value.func.id == "invarspec"
        except AttributeError:
            return False

        return node.value.args[0].value

    
    def visit_Expr(self, node):
        if invar := self.is_invarspec(node):
            self.INVARS.append(invar)
        else:
            self.generic_visit(node)

            
    def line_flow(self):
        out = "next(line) := case\n"
        
        for tupla in self.FLOW:
            if tupla[0] == "while":
                out += f"line = {tupla[2]} & {tupla[1]}: line + 1;\n"
                out += f"line = {tupla[2]}: {tupla[3]} + 1;\n"
                out += f"line = {tupla[3]}: {tupla[2]}; \n"
        out += f"line = {self.counter}: {self.counter}; \n" 
        out += "TRUE: line + 1; \n"
        out += "esac;\n\n"

        return out
        
        

    def transpile(self):
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

            for tupla in l:
                if tupla[0] == "increment":
                    sub_out += f"line = {tupla[1]}: {tupla[2]};\n"
            sub_out += f"TRUE: {var_name}; \n"
            sub_out += "esac;\n\n"

            out += sub_out

        for invar in self.INVARS:
            out += f"INVARSPEC {invar};\n"

        return out
    
######################################################

mv = MyVisitor()

def invarspec(s: str):
    pass


ex = """
i = 0
while (i < 10):
    i += 3
invarspec("i < 10")
"""


def run(code):
    mv = MyVisitor()
    mv.visit(ast.parse(code))
    open("out.smv", "w").write(mv.transpile())
    return mv


import astpretty
def pp(src):
    astpretty.pprint(ast.parse(src), show_offsets=False)

