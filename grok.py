#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 提取小说对话：修复字符串格式化与占位符冲突，并填充文件内容
import json
from pathlib import Path
from openai import OpenAI

qwen_api_key = "sk-xxxx"
qwen_base_url = "https://url"

# qwen_api_key="sk-y6VmA0IfcBkt6DDpS2JDHKoySMihQrrrjfr9qrHE1ziILk8y"
# qwen_base_url = "https://api.bltcy.ai/v1"
qwen_model_name = "grok-3"
qwen_client = OpenAI(api_key=qwen_api_key,base_url=qwen_base_url)

script_dir = Path(__file__).resolve().parent
json_input_path = script_dir / "data" / "test.json"

with open(json_input_path, "r", encoding="utf-8") as json_file:
    json_items = json.load(json_file)

if not isinstance(json_items, list):
    raise ValueError(f"Expected a JSON array in {json_input_path}, got {type(json_items).__name__}")

json_prefix = json_input_path.stem
output_dir = script_dir / "out" / json_prefix
output_dir.mkdir(parents=True, exist_ok=True)


def extract_text_from_delta(delta):
    if not delta:
        return ""
    if isinstance(delta, str):
        return delta
    if isinstance(delta, list):
        pieces = [extract_text_from_delta(item) for item in delta]
        return "".join(pieces)
    if isinstance(delta, dict):
        if "content" in delta:
            return extract_text_from_delta(delta["content"])
        if "text" in delta:
            text_value = delta["text"]
            return text_value if isinstance(text_value, str) else str(text_value)
        return ""
    content_attr = getattr(delta, "content", None)
    if content_attr is not None:
        return extract_text_from_delta(content_attr)
    text_attr = getattr(delta, "text", None)
    if text_attr is not None:
        return extract_text_from_delta(text_attr)
    return ""


for idx, item in enumerate(json_items):

    if isinstance(item, dict):
        cat_str = item.get("text", "")
    else:
        cat_str = str(item)
    
    if cat_str=="":
        continue

    identifier = f"{json_prefix}_{idx}"

#     system_prompt = '''
# 将当前文本中的全部对话提取出来，按照此格式[{'role': '角色','dialogue': '对话','expression': '表情','mood':'情绪'}]输出。

# {txt}
# '''
#     # 使模板可用于 str.format：转义所有花括号，仅保留 {txt}
#     _format_safe_template = (
#         system_prompt
#         .replace('{', '{{')
#         .replace('}', '}}')
#         .replace('{{txt}}', '{txt}')
#     )
#     prompt = _format_safe_template.format(txt=cat_str)

    prompt = [{
        "type":"text",
        "text":"帮我从此段文本中将全部对话提取出来，按照此格式{'role': '角色','dialogue': '对话','expression': '表情','mood':'情绪'}\"输出"
    },
    {
        "type":"text",
        "text":f"{identifier} \n{cat_str}"
    }
    ]

    print(prompt)
    messages = []
    # promp = """你是一个有帮助的AI助手。请根据用户提供的文本提取对话。"""
    # messages.append({"role": "system", "content": promp})
    messages.append({"role": "user", "content": prompt})
    assistant_reply_parts = []
    stream_error = None
    try:
        stream = qwen_client.chat.completions.create(
            model=qwen_model_name,
            messages=messages,
            temperature=0.7,
            top_p=1,
            max_tokens=40960,
            # presence_penalty=0.1,
            # frequency_penalty=0.1,
            stream=True
        )
        for chunk in stream:
            if isinstance(chunk, dict):
                choices = chunk.get("choices")
            else:
                choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            choice = choices[0]
            if isinstance(choice, dict):
                delta_text = extract_text_from_delta(choice.get("delta"))
                if not delta_text:
                    delta_text = extract_text_from_delta(choice.get("message"))
                if not delta_text:
                    delta_text = extract_text_from_delta(choice.get("content"))
            else:
                delta_text = extract_text_from_delta(getattr(choice, "delta", None))
                if not delta_text:
                    delta_text = extract_text_from_delta(getattr(choice, "message", None))
                if not delta_text:
                    delta_text = extract_text_from_delta(getattr(choice, "content", None))
            # print(delta_text)
            if delta_text:
                assistant_reply_parts.append(delta_text)
                print(delta_text, end="", flush=True)
    except Exception as error:
        stream_error = error
        print(f"\nStreaming error for entry {identifier}: {error}")
    finally:
        print()

    assistant_reply = "".join(assistant_reply_parts).strip()
    if not assistant_reply and stream_error is not None:
        print(f"No content received before error for entry {identifier}")

    json_path = output_dir / f"{idx}.json"
    text_path = output_dir / f"{idx}.txt"

    json_saved = False
    try:
        parsed_reply = json.loads(assistant_reply)
    except json.JSONDecodeError as decode_error:
        print(f"Failed to parse JSON for entry {identifier}: {decode_error}")
    else:
        try:
            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(parsed_reply, json_file, ensure_ascii=False, indent=2)
            print(f"JSON saved to {json_path}")
            json_saved = True
        except Exception as file_error:
            print(f"Failed to save JSON for entry {identifier}: {file_error}")

    if not json_saved:
        try:
            with open(text_path, "w", encoding="utf-8") as text_file:
                text_file.write(assistant_reply)
            print(f"Fallback text saved to {text_path}")
        except Exception as file_error:
            print(f"Failed to save fallback text for entry {identifier}: {file_error}")
