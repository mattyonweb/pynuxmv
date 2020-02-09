import ast

def nontrivial_range(loop_varname: str, args: list):
    """ When you have a `range()` like:

    for i in range(50, 133, x+1):

    you cannot be sure if the last argument (x+1) is > 0 or not. 
    Hence, if you want to transform a `for _ in range(_)` expression
    into a `while`, you have to build a more complex while condition
    such as:

    while ( (x+1 <  0 and i > 133) or 
            (x+1 >= 0 and i < 133)): 

    this template returns this "complex" condition. """

    return ast.Expr(
        value=ast.BoolOp(
                op=ast.Or(),
                values=[
                    ast.BoolOp(
                        op=ast.And(),
                        values=[
                            ast.Compare(
                                left=args[2],
                                ops=[ast.Lt()],
                                comparators=[ast.Constant(value=0, kind=None)],
                            ),
                            ast.Compare(
                                left=ast.Name(id=loop_varname, ctx=ast.Load()),
                                ops=[ast.Gt()],
                                comparators=[args[1]],
                            ),
                        ],
                    ),
                    ast.BoolOp(
                        op=ast.And(),
                        values=[
                            ast.Compare(
                                left=args[2],
                                ops=[ast.GtE()],
                                comparators=[ast.Constant(value=0, kind=None)],
                            ),
                            ast.Compare(
                                left=ast.Name(id=loop_varname, ctx=ast.Load()), 
                                ops=[ast.Lt()],
                                comparators=[args[1]],
                            ),
                        ],
                    ),
                ],
            ),
        ) 
