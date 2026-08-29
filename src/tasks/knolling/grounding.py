import os
import json
import base64
import asyncio
import logging
import random
import glob
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError
import argparse
from src.tasks.knolling.prompts.prompts import PROMPT_GROUNDING

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_KEY = os.environ.get("PRI_API_KEY")
BASE_URL = os.environ.get("PRI_URL")
aclient = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

def encode_image_sync(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def save_json_result(data, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def clean_json_text(text):
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return text.strip()
    except Exception:
        return text

def draw_and_save_visualization(image_path, data, output_path):
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            width, height = img.size
            draw = ImageDraw.Draw(img)
            
            font_size = max(14, int(width * 0.02))
            try:
                font = ImageFont.truetype("NotoSansCJK-Regular.ttc", font_size)
            except IOError:
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except IOError:
                    font = ImageFont.load_default()

            objects = data.get("objects", [])
            color_palette = ['red', 'green', 'blue', 'yellow', 'orange', 'cyan', 'magenta', 'lime']
            
            for i, obj in enumerate(objects):
                box = obj.get("box_2d", [])
                if len(box) != 4: continue
                
                norm_x1, norm_y1, norm_x2, norm_y2 = box
                abs_x1 = int(norm_x1 / 1000 * width)
                abs_y1 = int(norm_y1 / 1000 * height)
                abs_x2 = int(norm_x2 / 1000 * width)
                abs_y2 = int(norm_y2 / 1000 * height)

                if abs_x1 > abs_x2: abs_x1, abs_x2 = abs_x2, abs_x1
                if abs_y1 > abs_y2: abs_y1, abs_y2 = abs_y2, abs_y1
                
                color = color_palette[i % len(color_palette)]
                line_width = max(3, int(width * 0.005))
                draw.rectangle([abs_x1, abs_y1, abs_x2, abs_y2], outline=color, width=line_width)
                
                label = obj.get('label', 'unknown')
                attr_c = obj.get('color', '')
                
                text_content = f"{label} {attr_c}"
                
                if hasattr(font, "getbbox"):
                    text_bbox = draw.textbbox((abs_x1, abs_y1), text_content, font=font)
                else:
                    w_t, h_t = draw.textsize(text_content, font=font)
                    text_bbox = (abs_x1, abs_y1, abs_x1 + w_t, abs_y1 + h_t)

                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                text_x = abs_x1
                text_y = abs_y1 - text_height - 4
                if text_y < 0: text_y = abs_y1 + 4
                
                draw.rectangle([text_x, text_y, text_x + text_width + 4, text_y + text_height + 4], fill=color)
                draw.text((text_x + 2, text_y + 2), text_content, fill="black", font=font)

            img.save(output_path)
    except Exception as e:
        logger.error(f"Failed to save visualization for {image_path}: {e}")

async def query_model_for_class(
    target_class: str,
    image_url_obj: dict,
    dsl_colors: list,
    model: str,
    max_retries: int = 30
):
    current_vocab = [target_class]
    
    system_prompt = PROMPT_GROUNDING.format(
        object_classes=json.dumps(current_vocab, indent=4),
        colors=json.dumps(dsl_colors, indent=4),
        object_classes2=json.dumps(current_vocab, indent=4),
        colors2=json.dumps(dsl_colors, indent=4),
    )

    user_content = [{"type": "image_url", "image_url": image_url_obj}]

    for attempt in range(max_retries):
        try:

            response = await aclient.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1,
                max_tokens=2048
            )
            
            raw_content = response.choices[0].message.content
            cleaned_json_str = clean_json_text(raw_content)
            result_json = json.loads(cleaned_json_str)
            return result_json.get("objects", [])

        except json.JSONDecodeError:
            if attempt == max_retries - 1:
                logger.warning(f"  [Class: {target_class}] JSON parsing failed")
            await asyncio.sleep(1)
        except Exception as e:
            if attempt == max_retries - 1:
                logger.warning(f"  [Class: {target_class}] API error: {e}")
            await asyncio.sleep(1 + attempt)
    
    return []

async def process_single_image_aggregated(
    image_path: str,
    cases_dir: str,
    output_base_dir: str,
    dsl_global_config: dict,
    semaphore: asyncio.Semaphore,
    model: str
):
    try:
        file_name = Path(image_path).stem
        json_dir = os.path.join(output_base_dir, "json")
        img_out_dir = os.path.join(output_base_dir, "imgs")
        
        json_output_path = os.path.join(json_dir, f"{file_name}.json")
        img_output_path = os.path.join(img_out_dir, f"{file_name}_vis.png")

        case_path = os.path.join(cases_dir, f"{file_name}.json")
        
        target_classes = []
        if os.path.exists(case_path):
            try:
                with open(case_path, 'r', encoding='utf-8') as f:
                    case_data = json.load(f)
                    target_classes = case_data.get("object_classes", [])
                    
                    if not target_classes:
                        logger.warning(f"[{file_name}] not found target classes in case JSON.")
            except Exception as e:
                logger.error(f"[{file_name}] failed to read case JSON: {e}")
        else:
            logger.warning(f"[{file_name}] corresponding Case JSON not found: {case_path}")
            return None

        if not target_classes:
            logger.warning(f"[{file_name}] no target classes found, skipping processing")
            return None

        base64_image = await asyncio.to_thread(encode_image_sync, image_path)
        image_url_obj = {"url": f"data:image/jpeg;base64,{base64_image}"}

        colors_vocab = dsl_global_config.get("vocabulary", {}).get("attribute_values", {}).get("colors", ["red", "blue", "green", "black", "white", "yellow", "other"])

        aggregated_objects = []
        
        async with semaphore:
            logger.info(f"[{file_name}] start processing {target_classes}")
            
            tasks = [
                query_model_for_class(cls, image_url_obj, colors_vocab, model) 
                for cls in target_classes
            ]
            results = await asyncio.gather(*tasks)
            
            for objs in results:
                aggregated_objects.extend(objs)

        final_result = {
            "image_file": file_name,
            "objects": aggregated_objects
        }

        if aggregated_objects:
            await asyncio.gather(
                asyncio.to_thread(save_json_result, final_result, json_output_path),
                asyncio.to_thread(draw_and_save_visualization, image_path, final_result, img_output_path)
            )
            logger.info(f"[{file_name}] completed with {len(aggregated_objects)} objects.")
            return final_result
        else:
            logger.warning(f"[{file_name}] No objects detected.")
            save_json_result(final_result, json_output_path)
            return final_result
    except Exception as e:
        logger.error(f"[{image_path}] No objects detected. {e}", exc_info=True)
        return None

async def batch_process_benchmark(dsl, cases_dir, image_files, output_base_dir, concurrency_limit=5):
    os.makedirs(os.path.join(output_base_dir, "json"), exist_ok=True)
    os.makedirs(os.path.join(output_base_dir, "imgs"), exist_ok=True)

    sem = asyncio.Semaphore(concurrency_limit)
    tasks = []

    print(f"Found {len(image_files)} images, starting processing...")
    MODEL_NAME = "qwen3-vl-8b-instruct" 

    for img_path in image_files:
        task = asyncio.create_task(
            process_single_image_aggregated(
                img_path, 
                cases_dir, 
                output_base_dir, 
                dsl, 
                sem, 
                model=MODEL_NAME
            )
        )
        tasks.append(task)
    
    try:
        from tqdm.asyncio import tqdm
        results = await tqdm.gather(*tasks, desc="Aggregated Grounding")
    except ImportError:
        results = await asyncio.gather(*tasks)
        
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--concurrency_limit", type=int, default=1)
    args = parser.parse_args()

    DSL_PATH = "configs/dsl_knolling.json"
    INPUT_IMG_DIR = f"responses/knolling/{args.model}/imgs"
    CASES_DIR = "benchmarks/knolling"
    OUTPUT_BASE_DIR = f"responses/knolling/{args.model}/grounding"

    if os.path.exists(DSL_PATH):
        with open(DSL_PATH) as f:
            dsl = json.load(f)
    else:
        raise FileNotFoundError(f"DSL configuration file not found: {DSL_PATH}")

    image_extensions = ['*.png', '*.jpg', '*.jpeg']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(INPUT_IMG_DIR, ext)))
    image_files.sort()

    if not image_files:
        logger.error(f"No images found in {INPUT_IMG_DIR}")
        exit()
        
    if not os.path.exists(CASES_DIR):
        logger.error(f"Cases directory does not exist: {CASES_DIR}")
        exit()

    results = asyncio.run(batch_process_benchmark(
        dsl, 
        CASES_DIR,
        image_files, 
        OUTPUT_BASE_DIR, 
        concurrency_limit=args.concurrency_limit
    ))
    
    success_count = len([r for r in results if r and r.get("objects")])
    print(f"Processing complete: {success_count} / {len(image_files)} images successfully detected objects.")
