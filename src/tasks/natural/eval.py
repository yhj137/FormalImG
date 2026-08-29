import os
import json
import asyncio
import base64
import re
import time
import textwrap
import traceback
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
from openai import AsyncOpenAI
from src.tasks.natural.prompts.prompts import prompts_eval
import argparse


CASE_DIR = None
IMAGE_DIR = None

OUTPUT_VIS_DIR = None
OUTPUT_JSON_DIR = None

VLM_MODEL = "gemini-3-pro-preview"
CONCURRENCY_LIMIT = None
MAX_RETRIES = 10


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_json_from_text(text):
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end+1]
        else:
            raise ValueError("No JSON object found in response")
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            import ast
            return ast.literal_eval(json_str)
        except:
            raise ValueError(f"Failed to parse JSON: {json_str[:50]}...")

def get_cjk_font(size=20):
    font_paths = [
        "simhei.ttf", "msyh.ttc", "SimHei.ttf", 
        "/System/Library/Fonts/PingFang.ttc", 
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "arial.ttf"
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    print("Warning: CJK font not found, using default.")
    return ImageFont.load_default()

def print_matrix(data_dict, title, value_formatter):
    if not data_dict:
        print("No data for statistics.")
        return

    rows = sorted(list(set(k[1] for k in data_dict.keys()))) 
    cols = sorted(list(set(k[0] for k in data_dict.keys()))) 
    
    out_text = ""
    print(f"\n=== {title} ===")
    out_text += f"\n=== {title} ===\n"
    header = "Cnt\\Nrml |" + "".join([f"   {str(c):<3}  |" for c in cols])
    print("-" * len(header))
    out_text += "-" * len(header) + "\n"

    print(header)
    out_text += header + "\n"

    print("-" * len(header))
    out_text += "-" * len(header) + "\n"
    
    for r in rows:
        row_str = f"   {str(r):<3}    |"
        for c in cols:
            val = data_dict.get((c, r))
            row_str += f" {value_formatter(val)} |"
        print(row_str)
        out_text += row_str + "\n"
    with open(IMAGE_DIR.replace("/imgs", "/results.txt"), "w") as f:
        f.write(out_text)


def create_visualization(image_path, save_path, case_data, model_result):
    try:
        if os.path.exists(image_path):
            original_img = Image.open(image_path).convert("RGB")
        else:
            original_img = Image.new('RGB', (512, 512), (200, 200, 200))
        
        w, h = original_img.size
        
        ext_width = 800
        total_w = w + ext_width
        total_h = max(h, 900)
        
        new_img = Image.new('RGB', (total_w, total_h), (255, 255, 255))
        new_img.paste(original_img, (0, 0))
        
        draw = ImageDraw.Draw(new_img)
        
        font_title = get_cjk_font(28)
        font_header = get_cjk_font(22)
        font_text = get_cjk_font(18)
        font_code = get_cjk_font(16)
        
        x_offset = w + 30
        y_offset = 30
        max_text_width = ext_width - 60
        
        is_pass = model_result.get("satisfies_constraint", False)
        status_text = "PASSED" if is_pass else "FAILED"
        status_color = (0, 150, 0) if is_pass else (220, 0, 0)
        
        draw.text((x_offset, y_offset), f"Model Judgement: {status_text}", font=font_title, fill=status_color)
        y_offset += 50
        
        case_id = os.path.basename(save_path).split('.')[0]
        diff = case_data.get("k", -1)
        diff_str = f"Case ID: {case_id} | K = {diff}"
        draw.text((x_offset, y_offset), diff_str, font=font_text, fill=(50, 50, 50))
        y_offset += 40
        
        draw.text((x_offset, y_offset), "[Natural Language Constraint]:", font=font_header, fill=(0, 0, 180))
        y_offset += 30
        
        nl_text = case_data.get("prompt", "")
        char_per_line = int(max_text_width / 18) 
        wrapped_nl = textwrap.fill(nl_text, width=char_per_line)
        draw.text((x_offset, y_offset), wrapped_nl, font=font_text, fill=(0, 0, 0))
        
        bbox = draw.multiline_textbbox((x_offset, y_offset), wrapped_nl, font=font_text)
        y_offset += (bbox[3] - bbox[1]) + 30
        
        draw.text((x_offset, y_offset), "[CNF Logic]:", font=font_header, fill=(0, 0, 180))
        y_offset += 30
        
        cnf_text = case_data.get("cnf", "")
        wrapped_cnf = textwrap.fill(cnf_text, width=int(max_text_width / 9))
        draw.text((x_offset, y_offset), wrapped_cnf, font=font_code, fill=(80, 80, 80))
        
        bbox_cnf = draw.multiline_textbbox((x_offset, y_offset), wrapped_cnf, font=font_code)
        y_offset += (bbox_cnf[3] - bbox_cnf[1]) + 30
        
        draw.text((x_offset, y_offset), "[Satisfied Clauses Found by Model]:", font=font_header, fill=(0, 0, 180))
        y_offset += 30
        
        clauses = model_result.get("satisfied_clauses", [])
        if not clauses:
            draw.text((x_offset, y_offset), "(None)", font=font_text, fill=(150, 0, 0))
            y_offset += 30
        else:
            for idx, clause in enumerate(clauses):
                if y_offset > total_h - 50:
                    draw.text((x_offset, y_offset), "... (more clauses truncated)", font=font_text, fill=(100, 100, 100))
                    break
                
                line = f"{idx+1}. {clause}"
                wrapped_line = textwrap.fill(line, width=char_per_line)
                draw.text((x_offset, y_offset), wrapped_line, font=font_text, fill=(0, 100, 0))
                
                bbox_l = draw.multiline_textbbox((x_offset, y_offset), wrapped_line, font=font_text)
                y_offset += (bbox_l[3] - bbox_l[1]) + 10

        new_img.save(save_path)
        
    except Exception as e:
        print(f"Error creating visualization for {save_path}: {e}")
        traceback.print_exc()


async def process_case(semaphore, client, case_file):
    async with semaphore:
        base_name = os.path.splitext(case_file)[0]
        json_path = os.path.join(CASE_DIR, case_file)
        image_path = os.path.join(IMAGE_DIR, f"{base_name}.png")
        output_json_path = os.path.join(OUTPUT_JSON_DIR, case_file)
        output_vis_path = os.path.join(OUTPUT_VIS_DIR, f"{base_name}_eval.jpg")

        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
        except Exception:
            print(f"Error reading JSON: {case_file}")
            return None

        if not os.path.exists(image_path):
            print(f"Warning: Image not found for {base_name}")
            return None

        nl_text = case_data.get("prompt", "")
        cnf_text = case_data.get("cnf", "")

        prompt_content = prompts_eval.format(nl=nl_text, cnf=cnf_text)
        
        try:
            b64_img = encode_image(image_path)
        except Exception as e:
            print(f"Error encoding image {base_name}: {e}")
            return None

        result_json = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.chat.completions.create(
                    model=VLM_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_content},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{b64_img}"}
                                }
                            ]
                        }
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                raw_content = response.choices[0].message.content
                result_json = extract_json_from_text(raw_content)
                break
            except Exception as e:
                print(f"API Error {base_name} (Attempt {attempt+1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2)
        
        if not result_json:
            print(f"Failed to get valid result for {base_name}")
            return None

        try:
            with open(output_json_path, "w", encoding='utf-8') as f:
                json.dump(result_json, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving JSON {base_name}: {e}")

        create_visualization(image_path, output_vis_path, case_data, result_json)
        
        print(f"Finished: {base_name} -> {result_json.get('satisfies_constraint')}")

        diff = case_data.get("difficulty", {})
        d_norm = diff.get("normal_var_max", 0)
        d_cnt = diff.get("count_var_max", 0)
        
        is_success = result_json.get("satisfies_constraint", False)
        
        return (d_norm, d_cnt), is_success

async def main():
    global CASE_DIR
    global IMAGE_DIR
    global OUTPUT_VIS_DIR
    global OUTPUT_JSON_DIR
    global CONCURRENCY_LIMIT
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--concurrency", type=int, default=2)

    args = parser.parse_args()

    model = args.model
    task = "natural"

    CASE_DIR = f"benchmarks/{task}"
    IMAGE_DIR = f"responses/{task}/{model}/imgs"

    OUTPUT_VIS_DIR = f"responses/{task}/{model}/check"
    if not os.path.exists(OUTPUT_VIS_DIR): os.makedirs(OUTPUT_VIS_DIR)
    OUTPUT_JSON_DIR = f"responses/{task}/{model}/results"
    if not os.path.exists(OUTPUT_JSON_DIR): os.makedirs(OUTPUT_JSON_DIR)

    CONCURRENCY_LIMIT = args.concurrency

    os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)
    os.makedirs(OUTPUT_VIS_DIR, exist_ok=True)

    api_key = os.environ.get("PRI_API_KEY")
    base_url = os.environ.get("PRI_URL")
    
    if not api_key:
        print("Error: PRI_API_KEY environment variable not set.")
        return

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    if not os.path.exists(CASE_DIR):
        print(f"Error: Directory {CASE_DIR} does not exist.")
        return
        
    case_files = [f for f in os.listdir(CASE_DIR) if f.endswith('.json')]
    try:
        case_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
    except:
        case_files.sort()
        
    print(f"Found {len(case_files)} cases to process.")
    tasks = []
    for cf in case_files:
        tasks.append(process_case(semaphore, client, cf))

    results = await asyncio.gather(*tasks)

    stats = defaultdict(lambda: {'total': 0, 'pass': 0})
    
    valid_results_count = 0
    
    for res in results:
        if res is None: continue
        
        diff_key, is_pass = res
        stats[diff_key]['total'] += 1
        if is_pass:
            stats[diff_key]['pass'] += 1
        valid_results_count += 1

    acc_data = {}
    count_data = {}
    
    total_pass_all = 0
    total_cases_all = 0

    for key, val in stats.items():
        t = val['total']
        p = val['pass']
        acc = (p / t * 100) if t > 0 else 0.0
        
        acc_data[key] = acc
        count_data[key] = t
        
        total_pass_all += p
        total_cases_all += t

    print("\n" + "="*40)
    print("       EVALUATION STATISTICS       ")
    print("="*40)
    
    print_matrix(count_data, "Sample Count (Total)", lambda x: f"{x:^6}" if x is not None else "   -  ")
    print_matrix(acc_data, "Accuracy (%)", lambda x: f"{x:5.1f}%" if x is not None else "   -  ")
    
    print(f"\nOverall Summary:")
    print(f"Total Processed: {valid_results_count}")
    if total_cases_all > 0:
        print(f"Global Accuracy: {total_pass_all}/{total_cases_all} = {total_pass_all/total_cases_all*100:.2f}%")
    
    print(f"\nCheck visualization images in: {OUTPUT_VIS_DIR}")
    print(f"Check JSON results in: {OUTPUT_JSON_DIR}")

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    print(f"\nTotal execution time: {time.time() - start_time:.2f} seconds")
