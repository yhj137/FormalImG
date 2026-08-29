import math
import json
import os
import glob
from collections import defaultdict
import traceback
import textwrap
import re
import time

from PIL import Image, ImageDraw, ImageFont, ImageColor
from src.engine.predicate_lifting import hoist_exists_clauses
import argparse

class EvalResult:
    def __init__(self, success, message=None, children=None, payload=None):
        self.success = success
        self.message = message if message else ("Success" if success else "Failure")
        self.children = children or []
        self.payload = payload 
        self.is_vacuous = False 

    def __bool__(self):
        return self.success

    def __repr__(self):
        vacuous_tag = " [Vacuous]" if self.is_vacuous else ""
        return f"<Result: {self.success}{vacuous_tag}, {self.message}>"

    def tree_str(self, prefix="", is_last=True):
        connector = "└── " if is_last else "├── "
        child_prefix = "    " if is_last else "│   "
        icon = "✅" if self.success else "❌"
        extra = " (Vacuously True)" if self.success and self.is_vacuous else ""
        lines = [f"{prefix}{connector}{icon} {self.message}{extra}"]
        count = len(self.children)
        for i, child in enumerate(self.children):
            is_last_child = (i == count - 1)
            lines.append(child.tree_str(prefix + child_prefix, is_last_child))
        return "\n".join(lines)
    
    def trace(self):
        icon = "✅" if self.success else "❌"
        extra = " (Vacuously True)" if self.success and self.is_vacuous else ""
        lines = [f"{icon} {self.message}{extra}"]
        count = len(self.children)
        for i, child in enumerate(self.children):
            lines.append(child.tree_str("", i == count - 1))
        return "\n".join(lines)

def parse_lisp_expression(expression):
    expression = expression.replace('\n', ' ')
    token_pattern = re.compile(r"""[\(\)]|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s\(\)]+""")
    tokens = token_pattern.findall(expression)
    
    if not tokens: return []

    def read_from_tokens(token_list):
        if len(token_list) == 0: 
            raise SyntaxError('Unexpected EOF')
        token = token_list.pop(0)
        if token == '(':
            exp = []
            while len(token_list) > 0 and token_list[0] != ')':
                exp.append(read_from_tokens(token_list))
            if len(token_list) == 0:
                raise SyntaxError('Unexpected EOF: Missing closing )')
            token_list.pop(0)
            return exp
        elif token == ')':
            raise SyntaxError('Unexpected )')
        else:
            try: return int(token)
            except ValueError:
                try: return float(token)
                except ValueError:
                    if (token.startswith("'") and token.endswith("'")) or \
                       (token.startswith('"') and token.endswith('"')):
                        if len(token) >= 2:
                            return token[1:-1]
                    return token
    return read_from_tokens(tokens)

class GeometryHelper:
    @staticmethod
    def center(box):
        return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    @staticmethod
    def area(box):
        return max(0, box[2] - box[0]) * max(0, box[3] - box[1])
    
    @staticmethod
    def format_obj(obj):
        return f"[{obj.get('label', 'unknown')} at {obj.get('box_2d')}]"

    @staticmethod
    def iou(box_a, box_b):
        xA = max(box_a[0], box_b[0])
        yA = max(box_a[1], box_b[1])
        xB = min(box_a[2], box_b[2])
        yB = min(box_a[3], box_b[3])

        interWidth = max(0, xB - xA)
        interHeight = max(0, yB - yA)
        interArea = interWidth * interHeight

        if interArea == 0:
            return 0.0

        boxAArea = GeometryHelper.area(box_a)
        boxBArea = GeometryHelper.area(box_b)

        unionArea = min(boxAArea, boxBArea)
        
        if unionArea <= 0: return 0.0
        return interArea / unionArea

class PredicateLibrary:
    def __init__(self, w, h):
        self.W = w
        self.H = h

    def Is(self, obj, label):
        if obj.get('label') == label:
            return EvalResult(True, f"Object is '{label}'")
        return EvalResult(False, f"Type mismatch: Expected '{label}', got '{obj.get('label')}'")

    def Has(self, obj, val):
        props = [obj.get('color'), obj.get('material'), obj.get('shape')]
        if val in props:
            return EvalResult(True, f"Object has property '{val}'")
        return EvalResult(False, f"Property missing: Object {GeometryHelper.format_obj(obj)} does not have '{val}'.")

    def OnLeftSide(self, obj):
        cx, _ = GeometryHelper.center(obj['box_2d'])
        if cx < self.W / 2: return EvalResult(True)
        return EvalResult(False, f"Object {obj['label']} is not on left")

    def OnRightSide(self, obj):
        cx, _ = GeometryHelper.center(obj['box_2d'])
        if cx > self.W / 2: return EvalResult(True)
        return EvalResult(False, f"Object {obj['label']} is not on right")

    def OnTopSide(self, obj):
        _, cy = GeometryHelper.center(obj['box_2d'])
        if cy < self.H / 2: return EvalResult(True)
        return EvalResult(False, f"Object {obj['label']} is not on top")

    def OnBottomSide(self, obj):
        _, cy = GeometryHelper.center(obj['box_2d'])
        if cy > self.H / 2: return EvalResult(True)
        return EvalResult(False, f"Object {obj['label']} is not on bottom")
        
    def InCenter(self, obj):
        cx, cy = GeometryHelper.center(obj['box_2d'])
        w3, h3 = self.W/3, self.H/3
        if (w3 < cx < 2*w3) and (h3 < cy < 2*h3): return EvalResult(True)
        return EvalResult(False, f"Object {obj['label']} is not in center region")

    def LeftOf(self, a, b):
        a_right = a['box_2d'][2]
        b_center_x = GeometryHelper.center(b['box_2d'])[0]
        if a_right < b_center_x: return EvalResult(True)
        return EvalResult(False, f"{a['label']} is not LeftOf {b['label']}")

    def RightOf(self, a, b):
        a_left = a['box_2d'][0]
        b_center_x = GeometryHelper.center(b['box_2d'])[0]
        if a_left > b_center_x: return EvalResult(True)
        return EvalResult(False, f"{a['label']} is not RightOf {b['label']}")

    def Above(self, a, b):
        a_bottom = a['box_2d'][3]
        b_center_y = GeometryHelper.center(b['box_2d'])[1]
        if a_bottom < b_center_y: return EvalResult(True)
        return EvalResult(False, f"{a['label']} is not Above {b['label']}")

    def Below(self, a, b):
        a_top = a['box_2d'][1]
        b_center_y = GeometryHelper.center(b['box_2d'])[1]
        if a_top > b_center_y: return EvalResult(True)
        return EvalResult(False, f"{a['label']} is not Below {b['label']}")

    def AlignedHorizontally(self, a, b):
        diff = abs(GeometryHelper.center(a['box_2d'])[1] - GeometryHelper.center(b['box_2d'])[1])
        if diff < 100: return EvalResult(True)
        return EvalResult(False, f"Not AlignedHorizontally (diff={diff:.1f})")

    def AlignedVertically(self, a, b):
        diff = abs(GeometryHelper.center(a['box_2d'])[0] - GeometryHelper.center(b['box_2d'])[0])
        if diff < 100: return EvalResult(True)
        return EvalResult(False, f"Not AlignedVertically (diff={diff:.1f})")

    def LargerThan(self, a, b):
        area_a = GeometryHelper.area(a['box_2d'])
        area_b = GeometryHelper.area(b['box_2d'])
        if area_a > area_b: return EvalResult(True)
        return EvalResult(False, f"{a['label']} not LargerThan {b['label']}")

    def SmallerThan(self, a, b):
        area_a = GeometryHelper.area(a['box_2d'])
        area_b = GeometryHelper.area(b['box_2d'])
        if area_a < area_b: return EvalResult(True)
        return EvalResult(False, f"{a['label']} not SmallerThan {b['label']}")

    def Equals(self, a, b): return EvalResult(a == b, f"{a} == {b}")
    def GreaterThan(self, a, b): return EvalResult(a > b, f"{a} > {b}")
    def LessThan(self, a, b): return EvalResult(a < b, f"{a} < {b}")
    def GreaterThanOrEquals(self, a, b): return EvalResult(a >= b, f"{a} >= {b}")
    def LessThanOrEquals(self, a, b): return EvalResult(a <= b, f"{a} <= {b}")

class Interpreter:
    def __init__(self, model_data, timeout_sec=None):
        self.objects = model_data.get("objects", [])
        self.lib = PredicateLibrary(1000, 1000)
        self.timeout_sec = timeout_sec
        self.start_time = time.time() if timeout_sec else None

    def check_overlaps(self, threshold=0.5):
        n = len(self.objects)
        if n < 2: return EvalResult(True, "Overlap check passed (obj count < 2)")
        
        for i in range(n):
            for j in range(i + 1, n):
                obj_a = self.objects[i]
                obj_b = self.objects[j]
                
                box_a = obj_a.get('box_2d')
                box_b = obj_b.get('box_2d')
                
                if box_a and box_b:
                    iou_val = GeometryHelper.iou(box_a, box_b)
                    if iou_val > threshold:
                        msg = (f"FAIL: Heavy Overlap detected (IoU={iou_val:.2f}) "
                               f"between '{obj_a.get('label')}' (#{i}) and '{obj_b.get('label')}' (#{j})")
                        return EvalResult(False, msg)
        
        return EvalResult(True, "Overlap check passed")

    def format_arg(self, arg):
        if isinstance(arg, dict) and 'label' in arg:
            return f"Obj({arg['label']})"
        return str(arg)

    def eval(self, ast, context=None):
        if self.timeout_sec and (time.time() - self.start_time > self.timeout_sec):
            raise TimeoutError(f"Evaluation exceeded {self.timeout_sec} seconds")
        if context is None: context = {}

        if not isinstance(ast, list):
            if isinstance(ast, str):
                if ast.startswith('?'):
                    if ast not in context: return EvalResult(False, f"Unbound {ast}")
                    return context[ast]
                if ast.startswith("'") or ast.startswith('"'): return ast.strip("'\"")
            return ast

        op = ast[0]
        args = ast[1:]

        if op.lower() == 'and':
            children = []
            for arg in args:
                res = self.eval(arg, context)
                if not isinstance(res, EvalResult): res = EvalResult(bool(res))
                if not res.success:
                    children.append(res)
                    return EvalResult(False, "AND check failed", children=children)
                children.append(res)
            return EvalResult(True, "AND satisfied")

        if op.lower() == 'or':
            failures = []
            for arg in args:
                res = self.eval(arg, context)
                if not isinstance(res, EvalResult): res = EvalResult(bool(res))
                if res.success: return EvalResult(True, "OR satisfied", children=[res])
                failures.append(res)
            return EvalResult(False, "All OR branches failed", children=failures)

        if op.lower() == 'not':
            res = self.eval(args[0], context)
            if not isinstance(res, EvalResult): res = EvalResult(bool(res))
            if res.success: return EvalResult(False, f"NOT failed", children=[res])
            return EvalResult(True, "NOT satisfied")

        if op.lower() == 'implies':
            if len(args) != 2:
                raise ValueError(f"IMPLIES expects 2 arguments, got {len(args)}")
            
            antecedent_ast, consequent_ast = args
            
            antecedent_res = self.eval(antecedent_ast, context)
            if not isinstance(antecedent_res, EvalResult):
                antecedent_res = EvalResult(bool(antecedent_res))

            if not antecedent_res.success:
                msg = "IMPLIES holds (antecedent is false)"
                res = EvalResult(True, msg, children=[antecedent_res])
                res.is_vacuous = True 
                return res

            consequent_res = self.eval(consequent_ast, context)
            if not isinstance(consequent_res, EvalResult):
                consequent_res = EvalResult(bool(consequent_res))
            
            if consequent_res.success:
                msg = "IMPLIES holds (antecedent and consequent both true)"
                return EvalResult(True, msg, children=[antecedent_res, consequent_res])
            else:
                msg = "IMPLIES fails (antecedent true, consequent false)"
                return EvalResult(False, msg, children=[antecedent_res, consequent_res])

        if op.lower() == 'forall':
            var_name, body = args
            effective_trigger_count = 0
            
            for idx, obj in enumerate(self.objects):
                new_ctx = context.copy()
                new_ctx[var_name] = obj
                res = self.eval(body, new_ctx)
                if not isinstance(res, EvalResult): res = EvalResult(bool(res))
                
                if not res.success:
                    return EvalResult(False, f"Forall failed at Obj #{idx}", children=[res])
                
                if not getattr(res, 'is_vacuous', False):
                    effective_trigger_count += 1
            
            if effective_trigger_count == 0:
                return EvalResult(False, f"Forall failed: Logic held comfortably, but the antecedent condition was NEVER met (0 triggers).")

            return EvalResult(True, f"Forall {var_name} satisfied (Triggered {effective_trigger_count} times)")

        if op.lower() == 'exists':
            var_name, body = args
            trace_children = []
            for idx, obj in enumerate(self.objects):
                new_ctx = context.copy()
                new_ctx[var_name] = obj
                res = self.eval(body, new_ctx)
                if not isinstance(res, EvalResult): res = EvalResult(bool(res))
                if res.success:
                    return EvalResult(True, f"Exists {var_name} satisfied by Obj #{idx}", children=[res])
                else:
                    trace_children.append(EvalResult(False, f"Candidate #{idx} failed", children=[res]))
            return EvalResult(False, f"Exists {var_name} failed", children=trace_children)

        if op == 'Count':
            var_name, body = args
            count = 0
            for obj in self.objects:
                new_ctx = context.copy()
                new_ctx[var_name] = obj
                res = self.eval(body, new_ctx)
                if res: count += 1
            return count

        if hasattr(self.lib, op):
            func = getattr(self.lib, op)
            resolved_args = []
            for arg in args:
                val = self.eval(arg, context)
                resolved_args.append(val)
            res = func(*resolved_args)
            if not isinstance(res, EvalResult): res = EvalResult(bool(res))
            if not res.success: res.message = f"{op} -> {res.message}"
            return res

        raise ValueError(f"Unknown Op: {op}")

def print_matrix(data_dict, title, value_formatter):
    rows = sorted(list(set(k[1] for k in data_dict.keys()))) 
    cols = sorted(list(set(k[0] for k in data_dict.keys()))) 
    
    print(f"\n=== {title} ===")
    header = "Cnt\\Nrml |" + "".join([f"   {c:<3}  |" for c in cols])
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    for r in rows:
        row_str = f"   {r:<3}    |"
        for c in cols:
            val = data_dict.get((c, r))
            row_str += f" {value_formatter(val)} |"
        print(row_str)

def get_cjk_font(size=20):
    font_paths = [
        "simhei.ttf", "msyh.ttc", "/System/Library/Fonts/PingFang.ttc", 
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "arial.ttf"
    ]
    for path in font_paths:
        try: return ImageFont.truetype(path, size)
        except: continue
    print("Warning: CJK font not found, using default.")
    return ImageFont.load_default()

def save_check_image(img_path, save_path, info):
    try:
        if not os.path.exists(img_path):
            original_img = Image.new('RGB', (1024, 1024), (240, 240, 240))
            w, h = 1024, 1024
        else:
            original_img = Image.open(img_path).convert("RGB")
            w, h = original_img.size
        
        ext_width = 600
        min_height = 800 
        new_h = max(h, min_height)
        new_w = w + ext_width
        
        new_img = Image.new('RGB', (new_w, new_h), (255, 255, 255))
        new_img.paste(original_img, (0, 0))
        
        draw = ImageDraw.Draw(new_img)
        
        objects = info.get('objects', [])
        obj_font = get_cjk_font(16)
        
        for obj in objects:
            label = obj.get('label', 'obj')
            color_name = obj.get('color', 'green')
            bbox_norm = obj.get('box_2d', [0, 0, 0, 0]) 
            outline_color = 'red'

            x1 = bbox_norm[0] * (w / 1000.0)
            y1 = bbox_norm[1] * (h / 1000.0)
            x2 = bbox_norm[2] * (w / 1000.0)
            y2 = bbox_norm[3] * (h / 1000.0)
            
            draw.rectangle([x1, y1, x2, y2], outline=outline_color, width=3)
            
            label_text = f"{label} ({color_name})"
            text_bbox = draw.textbbox((x1, y1), label_text, font=obj_font)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
            
            label_y = y1 - text_h - 4
            if label_y < 0: label_y = y1 + 4
            
            draw.rectangle(
                [x1, label_y, x1 + text_w + 4, label_y + text_h + 4], 
                fill=outline_color
            )
            draw.text((x1 + 2, label_y + 2), label_text, fill="white", font=obj_font)

        font_title = get_cjk_font(30)
        font_text = get_cjk_font(18)
        font_mono = get_cjk_font(16)
        
        text_x = w + 20
        text_y = 20
        max_text_width = ext_width - 40 
        
        is_pass = info.get('result', False)
        status_text = "PASS" if is_pass else "FAIL"
        status_color = (0, 180, 0) if is_pass else (220, 0, 0) 
        
        draw.text((text_x, text_y), f"Result: {status_text}", font=font_title, fill=status_color)
        text_y += 50

        fail_msg = info.get('message', '')
        if not is_pass and fail_msg:
             draw.text((text_x, text_y), "[Fail Reason]:", font=font_text, fill=(200, 0, 0))
             text_y += 25
             char_per_line_msg = int(max_text_width / 18)
             wrapped_msg = textwrap.fill(fail_msg, width=char_per_line_msg)
             draw.text((text_x, text_y), wrapped_msg, font=font_text, fill=(200, 0, 0))
             bbox_msg = draw.multiline_textbbox((text_x, text_y), wrapped_msg, font=font_text)
             text_y += (bbox_msg[3] - bbox_msg[1]) + 20
        
        #diff = info.get('difficulty', {})
        diff_str = f"K = {info.get('difficulty', 'N/A')}"
        draw.text((text_x, text_y), diff_str, font=font_text, fill=(0, 0, 0))
        text_y += 40
        
        prompt = info.get('prompt', 'N/A')
        draw.text((text_x, text_y), "[Description]:", font=font_text, fill=(0, 0, 200))
        text_y += 25
        
        char_per_line = int(max_text_width / 18) 
        wrapped_prompt = textwrap.fill(prompt, width=char_per_line)
        draw.text((text_x, text_y), wrapped_prompt, font=font_text, fill=(0, 0, 0))
        
        bbox = draw.multiline_textbbox((text_x, text_y), wrapped_prompt, font=font_text)
        text_height = bbox[3] - bbox[1]
        text_y += text_height + 30
        
        cnf = info.get('cnf', 'N/A')
        draw.text((text_x, text_y), "[CNF Logic]:", font=font_text, fill=(0, 0, 200))
        text_y += 25
        
        char_per_line_cnf = int(max_text_width / 10) 
        wrapped_cnf = textwrap.fill(str(cnf), width=char_per_line_cnf)
        draw.text((text_x, text_y), wrapped_cnf, font=font_mono, fill=(50, 50, 50))
        
        new_img.save(save_path)
    except Exception as e:
        print(f"Error drawing check image for {img_path}: {e}")
        traceback.print_exc()

def run_evaluation():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    model = args.model
    task = "knolling"

    cases_dir = f"benchmarks/{task}"
    responses_dir = f"responses/{task}/{model}/grounding/json"
    imgs_source_dir = f"responses/{task}/{model}/grounding/imgs"
    
    check_output_dir = f"responses/{task}/{model}/grounding/check"
    if not os.path.exists(check_output_dir): os.makedirs(check_output_dir)
    results_dir = f"responses/{task}/{model}/results"
    if not os.path.exists(results_dir): os.makedirs(results_dir)
    
    stats = defaultdict(lambda: {'pass': 0, 'total': 0})
    case_files = glob.glob(os.path.join(cases_dir, "*.json"))
    print(f"Found {len(case_files)} case files.")
    
    processed_count = 0
    skipped_count = 0 
    
    for case_path in case_files:
        filename = os.path.basename(case_path) 
        file_id = os.path.splitext(filename)[0] 
        
        try:
            with open(case_path, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
                
            cnf_expr = hoist_exists_clauses(case_data.get("dsl"))
            difficulty = case_data.get("k", -1)
            prompt_text = case_data.get("prompt", "N/A")
            d_norm = case_data.get("k", -1)
            d_cnt = -1
            
            response_path = os.path.join(responses_dir, filename)
            if not os.path.exists(response_path): continue 
                
            with open(response_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)

            try:
                interpreter = Interpreter(model_data, timeout_sec=10.0)
                
                overlap_result = interpreter.check_overlaps(threshold=1.5)
                
                final_message = ""
                if not overlap_result.success:
                    result = EvalResult(False, overlap_result.message)
                    final_message = overlap_result.message
                else:
                    ast = parse_lisp_expression(cnf_expr)
                    try:
                        result = interpreter.eval(ast)
                        final_message = result.message
                    except TimeoutError:
                        print(f"⚠️ [TIMEOUT] Skipping {filename} (> 5s)")
                        skipped_count += 1
                        continue 
            except Exception as e:
                result = EvalResult(False, "Syntax Error")
                final_message = result.message


            
            stats[(d_norm, d_cnt)]['total'] += 1
            if result.success:
                stats[(d_norm, d_cnt)]['pass'] += 1
            
            img_filename_jpg = f"{file_id}.jpg"
            img_filename_png = f"{file_id}.png"
            
            img_full_path = os.path.join(imgs_source_dir, f"{file_id}_vis.jpg")
            if not os.path.exists(img_full_path):
                 img_full_path = os.path.join(imgs_source_dir, f"{file_id}_vis.png")
            if not os.path.exists(img_full_path):
                if os.path.exists(os.path.join(imgs_source_dir, img_filename_jpg)):
                    img_full_path = os.path.join(imgs_source_dir, img_filename_jpg)
                elif os.path.exists(os.path.join(imgs_source_dir, img_filename_png)):
                    img_full_path = os.path.join(imgs_source_dir, img_filename_png)

            check_save_path = os.path.join(check_output_dir, f"{file_id}_check.jpg")
            
            info_to_draw = {
                "result": bool(result),
                "message": final_message,
                "difficulty": difficulty,
                "prompt": prompt_text,
                "cnf": cnf_expr,
                "objects": model_data.get("objects", []) 
            }
            save_check_image(img_full_path, check_save_path, info_to_draw)

            output_json = {
                "result": bool(result),
                "fail_reason": final_message if not result else None,
                "difficulty": difficulty,
                "prompt": prompt_text,
                "cnf": cnf_expr
            }
            with open(os.path.join(results_dir, f"{file_id}.json"), "w") as f:
                json.dump(output_json, f, indent=4, ensure_ascii=False)

            processed_count += 1
            if processed_count % 50 == 0:
                print(f"Processed {processed_count} files...")
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            traceback.print_exc()

    acc_data = {}
    count_data = {}
    
    for key, val in stats.items():
        total = val['total']
        passed = val['pass']
        acc = (passed / total * 100) if total > 0 else 0.0
        acc_data[key] = acc
        count_data[key] = total

    print_matrix(count_data, "Sample Count", lambda x: f"{x:^6}" if x is not None else "   -  ")
    print_matrix(acc_data, "Accuracy (%)", lambda x: f"{x:5.1f}%" if x is not None else "   -  ")

    total_pass = sum(v['pass'] for v in stats.values())
    total_cases = sum(v['total'] for v in stats.values())
    
    print(f"\nSummary:")
    print(f"Total Processed: {total_cases}")
    print(f"Skipped (Timeout): {skipped_count}")
    if total_cases > 0:
        print(f"Overall Accuracy: {total_pass}/{total_cases} = {total_pass/total_cases*100:.2f}%")
        print(f"Check images saved to: {check_output_dir}")
    else:
        print("\nNo cases processed successfully.")

if __name__ == "__main__":
    run_evaluation()