import re

def parse_s_expression(s: str):
    s = s.replace('(', ' ( ').replace(')', ' ) ')
    tokens = s.split()
    
    def read_from_tokens(token_list):
        if len(token_list) == 0:
            raise SyntaxError("Unexpected EOF")
        token = token_list.pop(0)
        if token == '(':
            L = []
            while token_list[0] != ')':
                L.append(read_from_tokens(token_list))
            token_list.pop(0)
            return L
        elif token == ')':
            raise SyntaxError("Unexpected ')'")
        else:
            return token 
            
    return read_from_tokens(tokens)

def contains_variable(expression, var: str) -> bool:
    if not isinstance(expression, list):
        return expression == var
    return any(contains_variable(sub_exp, var) for sub_exp in expression)

def transform_expression(expr):
    if not isinstance(expr, list):
        return expr

    operator = expr[0]

    if operator == 'exists' and len(expr) == 3:
        var = expr[1]
        body = expr[2]

        transformed_body = transform_expression(body)
        
        if isinstance(transformed_body, list) and transformed_body[0] == 'and':
            clauses = transformed_body[1:]
            
            hoistable_clauses = [] 
            non_hoistable_clauses = []
            
            for clause in clauses:
                if contains_variable(clause, var):
                    non_hoistable_clauses.append(clause)
                else:
                    hoistable_clauses.append(clause)
            
            
            new_inner_expr = None
            if not non_hoistable_clauses:
                pass
            elif len(non_hoistable_clauses) == 1:
                new_inner_expr = ['exists', var, non_hoistable_clauses[0]]
            else:
                new_inner_expr = ['exists', var, ['and'] + non_hoistable_clauses]

            if not hoistable_clauses:
                return new_inner_expr or expr 
            else:
                final_clauses = hoistable_clauses
                if new_inner_expr:
                    final_clauses.append(new_inner_expr)
                
                if len(final_clauses) == 1:
                    return final_clauses[0]
                else:
                    return ['and'] + final_clauses
        else:
            return ['exists', var, transformed_body]
    
    else:
        return [operator] + [transform_expression(arg) for arg in expr[1:]]

def unparse_s_expression(expr) -> str:
    if not isinstance(expr, list):
        return str(expr)
    else:
        return f"({' '.join(unparse_s_expression(item) for item in expr)})"

def hoist_exists_clauses(dsl_string: str) -> str:
    parsed_expr = parse_s_expression(dsl_string)
    
    transformed_expr = transform_expression(parsed_expr)
    
    return unparse_s_expression(transformed_expr)

if __name__ == "__main__":
    dsl1 = "(exists ?monitor (exists ?camera (and (Is ?monitor 'monitor') (OnLeftSide ?monitor) (Is ?camera 'camera') (RightOf ?camera ?monitor) (AlignedVertically ?monitor ?camera) (forall ?scissors (implies (Is ?scissors 'scissors') (exists ?apple (exists ?pen (exists ?donut (exists ?bowl (exists ?hat (exists ?plate (exists ?headphones (and (Is ?apple 'apple') (Is ?pen 'pen') (Is ?donut 'donut') (Is ?bowl 'bowl') (Is ?hat 'hat') (Is ?plate 'plate') (Is ?headphones 'headphones') (RightOf ?scissors ?camera) (AlignedVertically ?scissors ?camera) (RightOf ?apple ?scissors) (AlignedVertically ?apple ?scissors) (RightOf ?pen ?apple) (AlignedVertically ?pen ?apple) (RightOf ?donut ?pen) (AlignedVertically ?donut ?pen) (RightOf ?bowl ?donut) (AlignedVertically ?bowl ?donut) (RightOf ?hat ?bowl) (AlignedVertically ?hat ?bowl) (LeftOf ?hat ?plate) (AlignedVertically ?hat ?plate) (LeftOf ?plate ?headphones) (AlignedVertically ?plate ?headphones))))))))))))))"
    dsl2 = "(exists ?jeans (and (Is ?jeans 'jeans') (forall ?sock (implies (Is ?sock 'sock') (exists ?laptop (exists ?pan (exists ?plate (exists ?scissors (exists ?spoon (exists ?fork (exists ?carrot (exists ?pen (and (Is ?laptop 'laptop') (Is ?pan 'pan') (Is ?plate 'plate') (Is ?scissors 'scissors') (Is ?spoon 'spoon') (Is ?fork 'fork') (Is ?carrot 'carrot') (Is ?pen 'pen') (Above ?jeans ?sock) (LargerThan ?jeans ?sock) (Above ?sock ?laptop) (Above ?laptop ?pan) (LargerThan ?pan ?laptop) (Above ?pan ?plate) (SmallerThan ?plate ?pan) (Above ?plate ?scissors) (Above ?scissors ?spoon) (Above ?spoon ?fork) (Above ?fork ?carrot) (Above ?carrot ?pen) (OnBottomSide ?pen))))))))))))))"
    dsl3 = "(exists ?monitor (exists ?shirt (exists ?drill (exists ?stapler (exists ?wrench (exists ?knife (exists ?sandwich (forall ?lighter (implies (Is ?lighter 'lighter') (exists ?apple (exists ?lemon (and (Is ?monitor 'monitor') (Is ?shirt 'shirt') (Is ?drill 'drill') (Is ?stapler 'stapler') (Is ?wrench 'wrench') (Is ?knife 'knife') (Is ?sandwich 'sandwich') (Above ?monitor ?shirt) (Above ?shirt ?drill) (AlignedHorizontally ?drill ?stapler) (AlignedHorizontally ?stapler ?wrench) (AlignedHorizontally ?wrench ?knife) (Above ?knife ?sandwich) (OnRightSide ?sandwich) (Is ?apple 'apple') (Is ?lemon 'lemon') (AlignedHorizontally ?lighter ?shirt) (Above ?lemon ?lighter) (Below ?apple ?lighter)))))))))))))"

    print("Original:\n", dsl1)
    print("\nTransformed:\n", hoist_exists_clauses(dsl1))
    print("\n" + "="*30 + "\n")

    print("Original:\n", dsl2)
    print("\nTransformed:\n", hoist_exists_clauses(dsl2))
    print("\n" + "="*30 + "\n")

    print("Original:\n", dsl3)
    print("\nTransformed:\n", hoist_exists_clauses(dsl3))
    print("\n" + "="*30 + "\n")