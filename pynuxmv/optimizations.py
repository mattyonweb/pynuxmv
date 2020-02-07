""" This file contains optimizations achievable at AST level. """

import ast

Optimization = ast.NodeTransformer

class OptRemoveAugAssign(Optimization):
    """ x += 1 becomes x = x + 1 """
    def visit_AugAssign(self, node):
        variable_store = node.target
        variable_load  = node.target
        variable_load.ctx = ast.Load()
        return (
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

class OptMergeNonInterferentAssignments(Optimization):
    """ Given a block of subsequents assignments that have no dependencies
    between each other, unify those assignments. Eg:

    z = 0
    a = 1
    b += 2
    
    becomes:

    z, a, b = 0, 1, b + 2
    
    (if OptRemoveAugAssign is applied before this optimization)"""
    
    def contains_other_vars_other_than(self, node, accepted_varnames):
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if child.id not in accepted_varnames:
                    return False
        return True
            
    def is_constant_assign(self, node):
        return (
            isinstance(node, ast.Assign) and
            (isinstance(node.value, ast.Constant) or
             self.contains_other_vars_other_than(node.value, node.targets[0].id)) #TODO [0]?!
        )
    
    def visit_While(self, node):
        blocks, subblock = list(), list()

        for cmd in node.body:
            if self.is_constant_assign(cmd):
                print("Found")
                subblock.append( (cmd.targets[0], cmd.value) )
            elif subblock == []:
                blocks.append(cmd)
            else:
                blocks.append(
                    ast.Assign(
                        targets=[ast.Tuple(elts=[sb[0] for sb in subblock],
                                       ctx=ast.Store())],
                        value=ast.Tuple(elts=[sb[1] for sb in subblock],
                                    ctx=ast.Load()),
                        type_ignores=[]
                    )
                )
                blocks.append(cmd)
                subblock = []
        if subblock != []:
            blocks.append(
                    ast.Assign(
                        targets=[ast.Tuple(elts=[sb[0] for sb in subblock],
                                       ctx=ast.Store())],
                        value=ast.Tuple(elts=[sb[1] for sb in subblock],
                                    ctx=ast.Load()),
                        type_ignores=[]
                    )
                )

        new_while = node
        new_while.body = blocks
        return new_while

defaults = [OptRemoveAugAssign(), OptMergeNonInterferentAssignments()]

def tests(src, opts):
    """ Debug function to show humanly readble results of the
    optimizations """
    ast_ = ast.parse(src)
    for opt in opts:
        ast_ = opt.visit(ast_)
    return tocode(ast_)
