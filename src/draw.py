import os
import json
import asyncio
import base64
import httpx
from openai import AsyncOpenAI
import io
from PIL import Image
import re
import argparse

PROMPT_STYLES = {
    "default": "",
    "diffusion": "",
    "raw": "",
}

MODEL_ROUTERS = {
    "gpt-image-1": {
        "type": "openai",
        "model_id": "gpt-image-1",
        "size": "1024x1024",
        "style_key": "default"
    },
    # ...
}

def save_image_sync(output_file, image_bytes):
    try:
        image_stream = io.BytesIO(image_bytes)
        with Image.open(image_stream) as img:
            current_w, current_h = img.size
            current_format = img.format

            if current_w == 1024 and current_h == 1024 and current_format == 'PNG':
                with open(output_file, "wb") as f:
                    f.write(image_bytes)
                return

            image_stream.seek(0)
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            if current_w != 1024 or current_h != 1024:
                img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
            
            img.save(output_file, format="PNG")
            
    except Exception as e:
        print(f"Image processing failed, saving original bytes. Error: {e}")
        with open(output_file, "wb") as f:
            f.write(image_bytes)

async def run_openai_logic(client: AsyncOpenAI, config, style_text, prompt):
    final_prompt = style_text + prompt
    response = await client.images.generate(
        model=config["model_id"],
        prompt=final_prompt,
        size=config.get("size", "1024x1024"),
        n=1
    )
    return base64.b64decode(response.data[0].b64_json.split(",")[-1])


async def generate_image(semaphore, openai_client, http_client, model_name, prompt, output_file, filename, env_config):
    config = MODEL_ROUTERS.get(model_name)
    if not config:
        print(f"Error: Model {model_name} not configured.")
        return

    style_key = config.get("style_key", "default")
    style_text = PROMPT_STYLES.get(style_key, "")

    async with semaphore:
        print(f"Start processing: {filename} [{model_name}] | Style: {style_key}")
        for i in range(100):
            try:
                image_bytes = None
                
                if config["type"] == "openai":
                    image_bytes = await run_openai_logic(openai_client, config, style_text, prompt)

                if image_bytes:
                    await asyncio.to_thread(save_image_sync, output_file, image_bytes)
                    print(f"Success: {filename}")
                    return
                else:
                    raise RuntimeError("Got empty image bytes")

            except Exception as e:
                err_str = str(e)
                if "TextIllegalDetected" in err_str or "ImageIllegalDetected" in err_str:
                    print(f"❌ Safety Filter Triggered: {filename} contains sensitive content. SKIPPING.")
                    with open(output_file + ".blocked", "w") as f:
                        f.write(err_str)
                    return 

                if "safety" in err_str.lower() or "blocked" in err_str.lower():
                     print(f"❌ Safety/Block detected: {filename}. SKIPPING.")
                     return

                wait_time = 60
                print(f"Error processing {filename} (Attempt {i+1}): {repr(e)} | Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

async def main(args):
    TASK = args.task
    MODEL = args.model

    CONCURRENCY_LIMIT = args.concurrency

    if TASK == "knolling":
        from src.tasks.knolling.prompts.prompts import prompt_style, prompt_style_diffusion
        PROMPT_STYLES["default"] = prompt_style
        PROMPT_STYLES["diffusion"] = prompt_style_diffusion
    elif TASK == "natural":
        from src.tasks.natural.prompts.prompts import prompt_style, prompt_style_diffusion
        PROMPT_STYLES["default"] = prompt_style
        PROMPT_STYLES["diffusion"] = prompt_style_diffusion
        
    TIMEOUT_CONFIG = httpx.Timeout(1200.0, connect=600.0)

    INPUT_DIR = f"benchmarks/{TASK}"
    OUTPUT_DIR = f"responses/{TASK}/{MODEL}/imgs/"
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    api_key = os.environ.get("PRI_API_KEY")
    base_url = os.environ.get("PRI_URL")
    
    env_config = {
        "api_key": api_key,
        "base_url": base_url
    }

    openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    limits = httpx.Limits(max_keepalive_connections=CONCURRENCY_LIMIT, max_connections=CONCURRENCY_LIMIT)
    async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG, limits=limits) as http_client:
        
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        tasks = []
        
        if not os.path.exists(INPUT_DIR):
            print(f"Error: Input directory '{INPUT_DIR}' does not exist.")
            return

        all_files = os.listdir(INPUT_DIR)
        json_files = [f for f in all_files if f.endswith('.json')]
        print(f"Found {len(json_files)} JSON files to process using model: {MODEL}")

        for filename in json_files:
            input_path = os.path.join(INPUT_DIR, filename)
            file_stem = os.path.splitext(filename)[0]
            output_path = os.path.join(OUTPUT_DIR, f"{file_stem}.png")
            
            if os.path.exists(output_path):
                 print(f"Skipping {filename}, already exists.")
                 continue

            try:
                with open(input_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                
                if "prompt" in data:
                    prompt = data["prompt"]
                    
                    task = generate_image(
                        semaphore, 
                        openai_client,
                        http_client,
                        MODEL, 
                        prompt, 
                        output_path,
                        filename,
                        env_config
                    )
                    tasks.append(task)
                else:
                    print(f"Skipping {filename}: key not found.")
                    
            except Exception as e:
                print(f"Error reading input file {filename}: {e}")

        if tasks:
            await asyncio.gather(*tasks)
        else:
            print("No tasks created.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--task", required=True, choices=["natural", "knolling"])
    parser.add_argument("--model", required=True, choices=list(MODEL_ROUTERS.keys()))

    parser.add_argument("--concurrency", type=int, default=2)

    args = parser.parse_args()
    asyncio.run(main(args))
