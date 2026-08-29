import re
from collections import defaultdict, deque
import json

class DSLProcessor:
    def __init__(self, dsl_config):
        self.config = dsl_config
        
        ops_config = dsl_config.get('operators', {})
        self.logic_ops = set(ops_config.get('logical_connectives', ['and', 'or', 'implies', 'iff']))
        self.quantifiers = set(ops_config.get('quantifiers', ['exists', 'forall']))
        self.negation = set(ops_config.get('negation', ['not']))
        self.all_logic_ops = self.logic_ops | self.quantifiers | self.negation

        self.signatures = {}
        self.quantity_ops = set()
        self.aggregators = set()
        
        for func in dsl_config.get('functions', {}).get('counting', []):
            name = func['name']
            self.aggregators.add(name)
            self.signatures[name] = {
                'arity': len(func['args']),
                'args': func['args'],
                'type': 'aggregator'
            }

        pred_groups = dsl_config.get('predicates', {})
        for group_name, preds in pred_groups.items():
            is_numeric_comp = (group_name == 'numerical_comparison')
            for p in preds:
                name = p['name']
                if is_numeric_comp:
                    self.quantity_ops.add(name)
                
                self.signatures[name] = {
                    'arity': len(p['args']),
                    'args': p['args'],
                    'type': 'quantity_op' if is_numeric_comp else 'predicate'
                }

        vocab = dsl_config.get('vocabulary', {})
        self.valid_objects = set(vocab.get('object_classes', []))
        
        self.valid_attributes = set()
        attr_vals = vocab.get('attribute_values', {})
        for key, val_list in attr_vals.items():
            self.valid_attributes.update(val_list)
    
    def tokenize(self, text):
        token_pattern = re.compile(r"""[\(\)]|'(?:[^'\\]|\\.)*'|"[^"\\]*"|[^\s\(\)]+""")
        return token_pattern.findall(text)

    def parse(self, tokens):
        if not tokens: raise SyntaxError("Unexpected EOF")
        token = tokens.pop(0)
        if token == '(':
            exp = []
            while True:
                if not tokens: raise SyntaxError("Unbalanced parentheses: missing ')'")
                if tokens[0] == ')':
                    tokens.pop(0)
                    break
                exp.append(self.parse(tokens))
            return exp
        elif token == ')': 
            raise SyntaxError("Unexpected ')' found.")
        else:
            try: return int(token)
            except:
                try: return float(token)
                except: return token

    def deparse(self, ast):
        if not isinstance(ast, list): return str(ast)
        content = " ".join(self.deparse(x) for x in ast)
        return f"({content})"


    def validate_syntax(self, ast):
        self._validate_scope_definition(ast, bound_vars=set())

        self._validate_domain_compliance(ast)

        self._validate_structure_context(ast)

    def _strip_quotes(self, s):
        if isinstance(s, str):
            if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
                return s[1:-1]
        return s

    def _validate_domain_compliance(self, node):
        if not isinstance(node, list) or not node: return

        op = node[0]

        if op in self.all_logic_ops:
            args = node[1:]
            
            if op in self.quantifiers:
                if len(args) != 2:
                    raise SyntaxError(f"Arity Error: Quantifier '{op}' expects exactly 2 arguments (variable, body), got {len(args)}.\n"
                                      f"Likely caused by missing ')' in the previous block.")

            elif op in self.negation:
                if len(args) != 1:
                    raise SyntaxError(f"Arity Error: Negation '{op}' expects exactly 1 argument, got {len(args)}.")

            elif op in {'implies', 'iff'}:
                if len(args) != 2:
                    raise SyntaxError(f"Arity Error: Operator '{op}' expects exactly 2 arguments, got {len(args)}.")
            

            for arg in args:
                if op in self.quantifiers and isinstance(arg, str) and arg.startswith('?'):
                    continue
                if isinstance(arg, list):
                    self._validate_domain_compliance(arg)
            return

        if op in self.signatures:
            sig = self.signatures[op]
            args = node[1:]
            
            if len(args) != sig['arity']:
                raise SyntaxError(f"Arity Mismatch: '{op}' expects {sig['arity']} arguments, got {len(args)}.")

            expected_types = sig['args']
            for i, (arg, exp_type) in enumerate(zip(args, expected_types)):
                if isinstance(arg, list):
                    self._validate_domain_compliance(arg)
                    continue
                
                if exp_type == 'variable':
                    if not (isinstance(arg, str) and arg.startswith('?')):
                        raise SyntaxError(f"Type Error: Argument {i+1} of '{op}' must be a variable, got '{arg}'.")

                if isinstance(arg, str) and arg.startswith('?'):
                    continue
                
                literal_val = self._strip_quotes(arg)
                
                if exp_type == 'object_class':
                    if literal_val not in self.valid_objects:
                        raise SyntaxError(f"Vocabulary Error: '{literal_val}' is not a valid object class in '{op}'.")
                elif exp_type == 'attribute':
                    if literal_val not in self.valid_attributes:
                        raise SyntaxError(f"Vocabulary Error: '{literal_val}' is not a valid attribute in '{op}'.")
            return

        raise SyntaxError(f"Undefined Operator: '{op}' is not defined in the DSL schema.")

    def _validate_structure_context(self, ast):
        clauses = []
        if isinstance(ast, list) and ast and ast[0] == 'and':
            clauses = ast[1:]
        else:
            clauses = [ast]

        for clause in clauses:
            if not isinstance(clause, list) or not clause: continue
            op = clause[0]

            if op in self.quantity_ops:
                self._validate_numeric_context(clause)
            else:
                self._validate_boolean_context(clause)

    def _validate_scope_definition(self, node, bound_vars):
        if isinstance(node, str):
            if node.startswith('?') and node not in bound_vars:
                raise SyntaxError(f"Undefined variable '{node}' found.")
            return

        if not isinstance(node, list) or not node: return

        op = node[0]
        if op in self.quantifiers or op in self.aggregators:
            if len(node) >= 2:
                var = node[1]
                new_bound = bound_vars | {var}
                if len(node) > 2:
                    self._validate_scope_definition(node[2], new_bound)
            return
        
        for arg in node[1:]:
            self._validate_scope_definition(arg, bound_vars)

    def _validate_numeric_context(self, node):
        op = node[0]
        if op in self.aggregators:
            var = node[1]
            body = node[2]
            self._validate_boolean_context(body)
            free_vars = self.get_free_variables(node)
            if free_vars:
                 raise SyntaxError(f"Invalid Count: Must be closed. Depends on: {free_vars}")
            return

        if op in self.quantity_ops:
            for arg in node[1:]:
                if isinstance(arg, list):
                    self._validate_numeric_context(arg)
            return

        if op in self.all_logic_ops:
             raise SyntaxError(f"Type Error: Logic operator '{op}' found inside numeric context.")

    def _validate_boolean_context(self, node):
        if not isinstance(node, list) or not node: return
        op = node[0]

        if op in self.quantity_ops:
            raise SyntaxError(f"Forbidden: Numeric comparison '{op}' found inside nested logic.")
        
        if op in self.aggregators:
            raise SyntaxError(f"Type Error: Aggregator '{op}' found in boolean context.")

        for arg in node[1:]:
            self._validate_boolean_context(arg)

    def get_free_variables(self, node, bound_vars=None):
        if bound_vars is None: bound_vars = set()
        if isinstance(node, str):
            if node.startswith('?') and node not in bound_vars:
                return {node}
            return set()
        if not isinstance(node, list) or not node: return set()

        op = node[0]
        if op in self.quantifiers or op in self.aggregators:
            var = node[1]
            if len(node) > 2:
                return self.get_free_variables(node[2], bound_vars | {var})
            return set()

        free_vars = set()
        for arg in node[1:]:
            free_vars.update(self.get_free_variables(arg, bound_vars))
        return free_vars


    def _rename_bound_vars(self, node, used=None, counters=None, subst=None):
        if used is None: used = set()
        if counters is None: counters = {}
        if subst is None: subst = {}

        if isinstance(node, str):
            if node.startswith('?') and node in subst:
                return subst[node]
            return node

        if not isinstance(node, list) or not node:
            return node

        op = node[0]
        if op in self.quantifiers or op in self.aggregators:
            var = node[1]
            base = var
            new_var = var
            if new_var in used:
                counters[base] = counters.get(base, 0) + 1
                new_var = f"{base}_{counters[base]}"
                while new_var in used:
                    counters[base] += 1
                    new_var = f"{base}_{counters[base]}"

            used.add(new_var)
            new_subst = subst.copy()
            new_subst[var] = new_var
            body = self._rename_bound_vars(node[2], used, counters, new_subst) if len(node) > 2 else []
            return [op, new_var, body]

        new_args = []
        for arg in node[1:]:
            new_args.append(self._rename_bound_vars(arg, used, counters, subst))
        return [op] + new_args

    def fix_missing_parentheses(self, dsl_text):
        tokens = []
        pattern = re.compile(r"""\s*(?:(\()|(\))|'([^']*)'|([^()\s]+))\s*""")
        
        for match in pattern.finditer(dsl_text):
            if match.group(1): tokens.append('(')
            elif match.group(2): tokens.append(')')
            elif match.group(3) is not None: tokens.append(f"'{match.group(3)}'")
            elif match.group(4): tokens.append(match.group(4))

        root = []
        stack = [root]

        for token in tokens:
            if token == '(':
                new_list = []
                stack[-1].append(new_list)
                stack.append(new_list)
            elif token == ')':
                if len(stack) > 1:
                    stack.pop()
            else:
                stack[-1].append(token)
        
        if not root: return ""
        ast_root = root[0] if root else []

        def _recursive_fix(node):
            """
            返回一个列表 [node, sibling1, sibling2...]
            """
            if not isinstance(node, list):
                return [node]
            
            fixed_children = []
            for child in node:
                fixed_children.extend(_recursive_fix(child))
            
            if len(fixed_children) > 0:
                op = fixed_children[0]
                if isinstance(op, str) and op.lower() in ['exists', 'forall']:
                    if len(fixed_children) > 3:
                        valid_node = fixed_children[:3]
                        overflow_nodes = fixed_children[3:]
                        return [valid_node] + overflow_nodes
            
            return [fixed_children]

        fixed_nodes = _recursive_fix(ast_root)
        
        if not fixed_nodes: return ""
        
        final_ast = fixed_nodes[0] if len(fixed_nodes) == 1 else ['and'] + fixed_nodes

        def _to_string(node):
            if isinstance(node, list):
                return f"({' '.join(_to_string(c) for c in node)})"
            return str(node)

        return _to_string(final_ast)
    
    def process_cnf(self, node):
        if not isinstance(node, list) or not node: return node
        op = node[0]

        if op in self.quantifiers:
            return [op, node[1], self.process_cnf(node[2])]

        if op == 'implies':
            return self.process_cnf(['or', ['not', node[1]], node[2]])
        
        if op == 'iff':
            return self.process_cnf(['and', ['implies', node[1], node[2]], ['implies', node[2], node[1]]])

        if op == 'not':
            child = node[1]
            if isinstance(child, list) and child:
                child_op = child[0]
                if child_op == 'not': return self.process_cnf(child[1])
                elif child_op == 'and': return self.process_cnf(['or'] + [['not', c] for c in child[1:]])
                elif child_op == 'or': return self.process_cnf(['and'] + [['not', c] for c in child[1:]])
                elif child_op == 'exists': return self.process_cnf(['forall', child[1], ['not', child[2]]])
                elif child_op == 'forall': return self.process_cnf(['exists', child[1], ['not', child[2]]])
                elif child_op == 'implies': return self.process_cnf(['and', child[1], ['not', child[2]]])
            return ['not', self.process_cnf(child)]

        if op == 'and':
            return self.flatten_and(['and'] + [self.process_cnf(arg) for arg in node[1:]])
        
        if op == 'or':
            flat_or = self.flatten_or(['or'] + [self.process_cnf(arg) for arg in node[1:]])
            if not isinstance(flat_or, list) or flat_or[0] != 'or': return flat_or
            
            args = flat_or[1:]
            
            for i, arg in enumerate(args):
                if isinstance(arg, list) and arg and arg[0] in self.quantifiers:
                    q_op = arg[0]
                    var = arg[1]
                    body = arg[2]
                    
                    new_or_args = args[:i] + [body] + args[i+1:]
                    new_or = ['or'] + new_or_args
                    
                    return self.process_cnf([q_op, var, new_or])

            return self.distribute_or_over_and(args)

        return [op] + [self.process_cnf(arg) for arg in node[1:]]

    def flatten_and(self, node):
        if not isinstance(node, list) or node[0] != 'and': return node
        new_args = []
        for arg in node[1:]:
            if isinstance(arg, list) and arg and arg[0] == 'and':
                new_args.extend(arg[1:])
            else:
                new_args.append(arg)
        return ['and'] + new_args

    def flatten_or(self, node):
        if not isinstance(node, list) or node[0] != 'or': return node
        new_args = []
        for arg in node[1:]:
            if isinstance(arg, list) and arg and arg[0] == 'or':
                new_args.extend(arg[1:])
            else:
                new_args.append(arg)
        if len(new_args) == 1: return new_args[0]
        return ['or'] + new_args

    def distribute_or_over_and(self, args):
        and_arg = None
        others = []
        for arg in args:
            if isinstance(arg, list) and arg and arg[0] == 'and':
                and_arg = arg
            else:
                others.append(arg)
        
        if and_arg is None:
            if len(others) == 1: return others[0]
            return ['or'] + others

        new_and_args = []
        for child in and_arg[1:]:
            new_or = self.process_cnf(['or'] + others + [child])
            new_and_args.append(new_or)
        
        return self.flatten_and(['and'] + new_and_args)

    def lift_quantifiers(self, node):
        if not isinstance(node, list) or not node: return node
        
        args = [self.lift_quantifiers(arg) for arg in node[1:]]
        op = node[0]
        
        if op in ['and', 'or']:
            for i, arg in enumerate(args):
                if isinstance(arg, list) and arg and arg[0] in self.quantifiers:
                    q_op = arg[0]
                    var = arg[1]
                    body = arg[2]
                    
                    new_args = args[:i] + [body] + args[i+1:]
                    inner_node = [op] + new_args
                    
                    if op == 'and': inner_node = self.flatten_and(inner_node)
                    elif op == 'or': inner_node = self.flatten_or(inner_node)
                    
                    return self.lift_quantifiers([q_op, var, inner_node])
        
        return [op] + args

    def split_clauses_by_type(self, ast):
        clauses = []
        if isinstance(ast, list) and ast and ast[0] == 'and':
            clauses = ast[1:]
        else:
            clauses = [ast]

        normal_clauses = []
        quantity_clauses = []

        for clause in clauses:
            if not isinstance(clause, list) or not clause: continue
            op = clause[0]
            if op in self.quantity_ops:
                quantity_clauses.append(clause)
            else:
                normal_clauses.append(clause)
        return normal_clauses, quantity_clauses

    def isolate_single_clause(self, clause):
        prenex_clause = self.lift_quantifiers(clause)

        quantifier_chain = []
        current = prenex_clause
        while isinstance(current, list) and current and current[0] in self.quantifiers:
            quantifier_chain.append((current[0], current[1]))
            current = current[2]
            
        sub_clauses = []
        if isinstance(current, list) and current and current[0] == 'and':
            sub_clauses = current[1:]
        else:
            sub_clauses = [current]
        
        if not sub_clauses: return []

        sc_vars = [self.get_free_variables(sc) for sc in sub_clauses]
        
        n = len(sub_clauses)
        adj = defaultdict(list)
        var_map = defaultdict(list)
        for idx, vset in enumerate(sc_vars):
            for v in vset:
                var_map[v].append(idx)
        
        for v, indices in var_map.items():
            for i in range(len(indices)-1):
                adj[indices[i]].append(indices[i+1])
                adj[indices[i+1]].append(indices[i])
                
        visited = [False] * n
        groups = []
        for i in range(n):
            if not visited[i]:
                comp = []
                q = deque([i])
                visited[i] = True
                while q:
                    u = q.popleft()
                    comp.append(u)
                    for v in adj[u]:
                        if not visited[v]:
                            visited[v] = True
                            q.append(v)
                groups.append(comp)
                
        final_asts = []
        for grp_idx in groups:
            bodies = [sub_clauses[i] for i in grp_idx]
            if len(bodies) == 1:
                base = bodies[0]
            else:
                base = ['and'] + bodies
            
            needed_vars = set()
            for i in grp_idx:
                needed_vars.update(sc_vars[i])
            
            relevant_qs = [q for q in quantifier_chain if q[1] in needed_vars]
            
            res = base
            for op, var in reversed(relevant_qs):
                res = [op, var, res]
            
            final_asts.append(res)
            
        return final_asts

    def process_count_body_for_isolation(self, node):
        if not isinstance(node, list) or not node: return node
        
        if node[0] in self.aggregators:
            var = node[1]
            body = node[2]
            isolated_groups = self.isolate_single_clause(body)
            if not isolated_groups: new_body = body 
            elif len(isolated_groups) == 1: new_body = isolated_groups[0]
            else: new_body = ['and'] + isolated_groups
            return [node[0], var, new_body]

        return [node[0]] + [self.process_count_body_for_isolation(arg) for arg in node[1:]]

    def _count_quantifiers_and_clauses(self, node):
        q_count = 0
        current = node
        while isinstance(current, list) and current and current[0] in self.quantifiers:
            q_count += 1
            current = current[2]
        
        c_count = 0
        if isinstance(current, list) and current:
            if current[0] == 'and':
                c_count = len(current) - 1
            else:
                c_count = 1
        return q_count, c_count

    def calculate_difficulty(self, normal_groups, quantity_groups):
        unique_objects = set()

        def collect_objects(node):
            if not isinstance(node, list) or not node: return
            
            if node[0] == 'Is' and len(node) >= 3:
                obj_class = self._strip_quotes(node[2])
                unique_objects.add(obj_class)
            
            for arg in node[1:]:
                collect_objects(arg)

        for group in normal_groups:
            collect_objects(group)
        for group in quantity_groups:
            collect_objects(group)

        normal_vars_list = []
        normal_clauses_sum = 0
        for group in normal_groups:
            q_cnt, c_cnt = self._count_quantifiers_and_clauses(group)
            normal_vars_list.append(q_cnt)
            normal_clauses_sum += c_cnt
        d_normal_max = max(normal_vars_list) if normal_vars_list else 0
        s_normal_sum = normal_clauses_sum

        count_vars_list = []
        count_clauses_sum = 0
        def scan_quantity_clause(node):
            if not isinstance(node, list) or not node: return
            if node[0] in self.aggregators:
                body = node[2]
                inner_q, inner_c = self._count_quantifiers_and_clauses(body)
                count_vars_list.append(1 + inner_q)
                nonlocal count_clauses_sum
                count_clauses_sum += inner_c
                return
            for arg in node[1:]:
                scan_quantity_clause(arg)

        for q_clause in quantity_groups:
            scan_quantity_clause(q_clause)
        
        d_count_max = max(count_vars_list) if count_vars_list else 0
        s_count_sum = count_clauses_sum

        return {
            "object_class_count": len(unique_objects),
            "object_classes": list(unique_objects),
            "normal_var_max": d_normal_max,
            "normal_clause_sum": s_normal_sum,
            "count_var_max": d_count_max,
            "count_clause_sum": s_count_sum
        }

    def analyze(self, dsl_string):
        tokens = self.tokenize(dsl_string)
        ast = self.parse(tokens)
        if tokens: raise SyntaxError("Unbalanced parentheses.")

        print("Parsed:", json.dumps(ast))

        self.validate_syntax(ast)

        ast = self._rename_bound_vars(ast)
        cnf_ast = self.process_cnf(ast)
        
        normal_list, quantity_list = self.split_clauses_by_type(cnf_ast)
        
        final_normal_groups = []
        for n_clause in normal_list:
            final_normal_groups.extend(self.isolate_single_clause(n_clause))
        
        final_quantity_list = [self.process_count_body_for_isolation(q) for q in quantity_list]
        
        metrics = self.calculate_difficulty(final_normal_groups, final_quantity_list)
        
        all_groups = final_normal_groups + final_quantity_list
        if not all_groups: final_str = ""
        elif len(all_groups) == 1: final_str = self.deparse(all_groups[0])
        else: final_str = self.deparse(['and'] + all_groups)
            
        return final_str, metrics


if __name__ == "__main__":
    import traceback

    full_config = {
        "vocabulary": {
            "object_classes": [
                "laptop", "mouse", "keyboard", "monitor", "phone",
                "apple", "orange", "banana", "table", "chair" 
            ],
            "attribute_values": {
                "colors": ["red", "green", "blue", "yellow", "black", "white"]
            }
        },
        "functions": {
            "counting": [
                {
                    "name": "Count",
                    "args": ["variable", "condition"],
                    "returns": "number"
                }
            ]
        },
        "predicates": {
            "unary_attributes": [
                {"name": "Is", "args": ["variable", "object_class"]},
                {"name": "Has", "args": ["variable", "attribute"]}
            ],
            "unary_position_absolute": [
                {"name": "InCenter", "args": ["variable"]}
            ],
            "binary_position_relative": [
                {"name": "LeftOf", "args": ["variable", "variable"]},
                {"name": "RightOf", "args": ["variable", "variable"]}
            ],
            "numerical_comparison": [
                {"name": "Equals", "args": ["term", "term"]},
                {"name": "GreaterThan", "args": ["term", "term"]}
            ]
        },
        "operators": {
            "logical_connectives": ["and", "or", "implies", "iff"],
            "quantifiers": ["exists", "forall"],
            "negation": ["not"]
        }
    }

    processor = DSLProcessor(full_config)
    
    print("========================================")
    print("Start Running 40 Unit Tests")
    print("========================================")

    test_count = 0
    pass_count = 0

    def run_test(name, dsl_str, should_fail=False, error_msg_snippet=None, expected_metrics=None):
        global test_count, pass_count
        test_count += 1
        print(f"\n[Test {test_count}] {name}")
        print(f"Input: {dsl_str}")
        
        try:
            res_str, metrics = processor.analyze(dsl_str)
            if should_fail:
                print(f"❌ FAILED: Expected error containing '{error_msg_snippet}', but analysis succeeded.")
                print(f"   Result: {res_str}")
                return
            
            print(f"✅ PASSED (Success)")
            print(f"   Output: {res_str}")
            if expected_metrics:
                match = True
                for k, v in expected_metrics.items():
                    if metrics.get(k) != v:
                        match = False
                        print(f"   ⚠️ Metric Mismatch: {k} expected {v}, got {metrics.get(k)}")
                if match:
                    print(f"   Metrics Verified: OK")
            pass_count += 1

        except Exception as e:
            if should_fail:
                print(f"✅ PASSED (Caught expected error): {e}")
                pass_count += 1
            else:
                print(f"❌ FAILED: Unexpected Exception: {e}")

    run_test("Basic Existence", 
             "(exists ?x (Is ?x 'apple'))")
    
    run_test("Basic AND logic", 
             "(exists ?x (and (Is ?x 'laptop') (Has ?x 'red')))")
    
    run_test("Basic Count (Numeric Context)", 
             "(Equals (Count ?x (Is ?x 'mouse')) 2)",
             expected_metrics={"count_var_max": 1, "count_clause_sum": 1})

    run_test("String with parentheses (Tokenizer Check)", 
             "(exists ?x (Is ?x 'laptop (gaming)'))", 
             should_fail=True, error_msg_snippet="Vocabulary Error") 

    run_test("Valid String in Vocabulary", 
             "(exists ?x (Is ?x 'laptop'))")

    run_test("Unknown Object Class", 
             "(exists ?x (Is ?x 'spaceship'))", 
             should_fail=True, error_msg_snippet="not a valid object class")

    run_test("Unknown Attribute", 
             "(exists ?x (Has ?x 'shiny'))", 
             should_fail=True, error_msg_snippet="not a valid attribute")

    run_test("Unknown Predicate", 
             "(exists ?x (Flying ?x))", 
             should_fail=True, error_msg_snippet="Undefined Operator")

    run_test("Unknown Logic Operator", 
             "(exists ?x (xor (Is ?x 'apple') (Is ?x 'orange')))", 
             should_fail=True, error_msg_snippet="Undefined Operator")

    run_test("Literal instead of Variable", 
             "(Is 'apple' 'apple')", 
             should_fail=True, error_msg_snippet="Undefined variable")

    run_test("Is missing argument", 
             "(exists ?x (Is ?x))", 
             should_fail=True, error_msg_snippet="Arity Mismatch")

    run_test("LeftOf extra argument", 
             "(exists ?x (exists ?y (LeftOf ?x ?y ?z)))", 
             should_fail=True, error_msg_snippet="Arity Mismatch")

    run_test("Count missing body", 
             "(Equals (Count ?x) 5)", 
             should_fail=True, error_msg_snippet="Arity Mismatch")

    run_test("Free variable usage", 
             "(Is ?x 'apple')", 
             should_fail=True, error_msg_snippet="Undefined variable")

    run_test("Variable defined in sibling scope", 
             "(and (exists ?x (Is ?x 'apple')) (Is ?x 'orange'))", 
             should_fail=True, error_msg_snippet="Undefined variable")

    run_test("Correct nested scope", 
             "(exists ?x (and (Is ?x 'apple') (exists ?y (LeftOf ?y ?x))))")

    run_test("Count inside boolean logic (Nested)", 
             "(exists ?x (and (Is ?x 'apple') (Equals (Count ?y (Is ?y 'orange')) 1)))", 
             should_fail=True, error_msg_snippet="Forbidden: Numeric comparison")

    run_test("Raw Count in boolean", 
             "(exists ?x (and (Is ?x 'apple') (Count ?y (Is ?y 'orange'))))", 
             should_fail=True, error_msg_snippet="Type Error: Aggregator")

    run_test("Logic inside Numeric (Type Error)", 
             "(Equals (and (Is ?x 'apple')) 5)", 
             should_fail=True, error_msg_snippet="Logic operator 'and' found inside numeric context")

    run_test("Top-level AND with mixed types (Valid)", 
             "(and (exists ?x (Is ?x 'apple')) (Equals (Count ?y (Is ?y 'orange')) 2))")

    run_test("Open Count (Dependency on external var)", 
             "(exists ?x (Equals (Count ?y (LeftOf ?y ?x)) 1))", 
             should_fail=True) 
             
    run_test("Open Count Check", 
             "(and (exists ?x (Is ?x 'apple')) (Equals (Count ?y (LeftOf ?y ?x)) 1))",
             should_fail=True, error_msg_snippet="Must be closed")

    run_test("Implies Expansion", 
             "(forall ?x (implies (Is ?x 'apple') (Has ?x 'red')))")

    run_test("Iff Expansion", 
             "(forall ?x (iff (Is ?x 'apple') (Has ?x 'red')))")

    run_test("Not Not Elimination", 
             "(exists ?x (not (not (Is ?x 'apple'))))")

    run_test("De Morgan's Law (Not And)", 
             "(exists ?x (not (and (Is ?x 'apple') (Has ?x 'red'))))")

    run_test("Variable Shadowing", 
             "(and (exists ?x (Is ?x 'apple')) (exists ?x (Is ?x 'orange')))")

    run_test("Nested Shadowing", 
             "(exists ?x (and (Is ?x 'apple') (exists ?x (Has ?x 'red'))))")

    run_test("Count Variable Shadowing", 
             "(and (exists ?x (Is ?x 'apple')) (Equals (Count ?x (Is ?x 'monitor')) 1))")

    run_test("Disconnected Components (Split)", 
             "(exists ?x (exists ?y (and (Is ?x 'apple') (Is ?y 'orange'))))")

    run_test("Connected Components (Chain)", 
             "(exists ?x (exists ?y (and (Is ?x 'apple') (LeftOf ?x ?y) (Is ?y 'orange'))))")

    run_test("Mixed Connected/Disconnected", 
             "(exists ?x (exists ?y (exists ?z (and (Is ?x 'A') (Is ?y 'B') (LeftOf ?y ?z)))))",
             should_fail=True, error_msg_snippet="Vocabulary")
    
    run_test("Mixed Components (Valid Objects)", 
             "(exists ?x (exists ?y (exists ?z (and (Is ?x 'apple') (Is ?y 'orange') (LeftOf ?y ?z)))))",
             expected_metrics={"normal_var_max": 2}) 

    run_test("Zero Var (Only Count)", 
             "(Equals (Count ?x (Is ?x 'apple')) 5)",
             expected_metrics={"normal_var_max": 0, "count_var_max": 1, "count_clause_sum": 1})

    run_test("Simple Predicate Count", 
             "(exists ?x (and (Is ?x 'apple') (Has ?x 'red')))",
             expected_metrics={"normal_var_max": 1, "normal_clause_sum": 2, "count_var_max": 0})

    run_test("Complex Count Body", 
             "(Equals (Count ?x (exists ?y (and (Is ?x 'table') (Is ?y 'apple') (LeftOf ?y ?x)))) 1)",
             expected_metrics={"count_var_max": 2}) 

    run_test("Count Body Disconnected Split", 
             "(Equals (Count ?x (exists ?y (and (Is ?x 'table') (Is ?y 'apple')))) 1)",
             expected_metrics={"count_var_max": 1}) 
    
    run_test("Grand Integration Test", 
             """
             (and 
                (exists ?x (exists ?y 
                    (and (Is ?x 'laptop') (Is ?y 'mouse') (LeftOf ?y ?x))
                ))
                (exists ?z (Is ?z 'monitor'))
                (Equals (Count ?a (Is ?a 'apple')) 3)
             )
             """,
             expected_metrics={
                 "normal_var_max": 2,   
                 "normal_clause_sum": 4, 
                 "count_var_max": 1,
                 "count_clause_sum": 1
             })

    run_test("Negative Logic Complexity", 
             "(exists ?x (and (Is ?x 'apple') (not (exists ?y (LeftOf ?y ?x)))))",
             expected_metrics={"normal_var_max": 2}) 

    print("========================================")
    print(f"Tests Completed. Passed: {pass_count}/{test_count}")
    print("========================================")