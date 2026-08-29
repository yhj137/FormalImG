import os
import json
import asyncio
import base64
from openai import AsyncOpenAI
from src.tasks.knolling.prompts.prompts import prompt_style_llm


import re
import json
import ast

import argparse

def extract_json_list(text):
    markdown_pattern = r"```(?:json)?\s*(\[\s*\{.*\}\s*\])\s*```"
    match = re.search(markdown_pattern, text, re.DOTALL)
    
    if match:
        json_str = match.group(1)
    else:
        list_pattern = r"(\[\s*\{.*\}\s*\])" 
        match = re.search(list_pattern, text, re.DOTALL)
        
        if match:
            json_str = match.group(1)
        else:
            start = text.find('[')
            end = text.rfind(']')
            if start != -1 and end != -1 and end > start:
                json_str = text[start:end+1]
            else:
                raise ValueError("No JSON list found in response")

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(json_str)
        except:
            raise ValueError(f"Failed to parse extracted JSON: {json_str[:50]}...")

async def generate_layout(semaphore, client, model, dsl, prompt, output_file, file_stem, filename):
    async with semaphore:
        print(f"Start processing: {filename}")
        for i in range(100):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt_style_llm.format(
                                objs=dsl["vocabulary"]["object_classes"],
                                colors=dsl["vocabulary"]["attribute_values"]["colors"]
                            ) + prompt
                        }
                    ],
                    temperature=1.0,
                )
                
                response_content = response.choices[0].message.content
                
                if "</think>" in response_content:
                    response_content = response_content.split("</think>")[-1]
                
                try:
                    generated_objs = extract_json_list(response_content)
                    generated_data = {"image_file": file_stem, "objects": generated_objs}
                except ValueError as ve:
                    print(f"JSON Extraction failed for {filename}: {ve}")
                    generated_data = {"image_file": file_stem, "objects": None}

                with open(output_file, "w") as f:
                    json.dump(generated_data, f, indent=4, ensure_ascii=False)
                
                print(f"Success: {filename}")
                return
            except Exception as e:
                print(f"Error processing {filename} (Attempt {i+1}): {e}")
                await asyncio.sleep(60)

async def main(args):
    MODEL = args.model
    CONCURRENCY_LIMIT = args.concurrency

    DSL_PATH = f"configs/dsl_knolling.json"
    INPUT_DIR = f"benchmarks/knolling"
    OUTPUT_DIR = f"responses/knolling/{MODEL}/grounding/json/"

    with open(DSL_PATH, "r") as f:
        DSL_DOMAIN = json.load(f)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    api_key = None
    base_url = None

    api_key = os.environ.get("PRI_API_KEY")
    base_url = os.environ.get("PRI_URL")

    client = AsyncOpenAI(
        api_key=api_key, 
        base_url=base_url
    )
    
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = []
    
    if not os.path.exists(INPUT_DIR):
        print(f"Error: Input directory '{INPUT_DIR}' does not exist.")
        return

    all_files = os.listdir(INPUT_DIR)
    
    json_files = [f for f in all_files if f.endswith('.json')]
    print(f"Found {len(json_files)} JSON files to process.")

    for filename in json_files:
        input_path = os.path.join(INPUT_DIR, filename)
        file_stem = os.path.splitext(filename)[0]
        output_path = os.path.join(OUTPUT_DIR, f"{file_stem}.json")
        
        try:
            with open(input_path, "r", encoding='utf-8') as f:
                data = json.load(f)
            
            if "prompt" in data:
                prompt = data["prompt"]
                
                task = generate_layout(
                    semaphore, 
                    client, 
                    MODEL, 
                    DSL_DOMAIN,
                    prompt, 
                    output_path,
                    file_stem,
                    filename
                )
                tasks.append(task)
            else:
                print(f"Skipping {filename}: key 'prompt' not found.")
                
        except Exception as e:
            print(f"Error reading input file {filename}: {e}")

    if tasks:
        await asyncio.gather(*tasks)
    else:
        print("No tasks created.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()

    asyncio.run(main(args))