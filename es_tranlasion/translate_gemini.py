import os
import re
import json
import hashlib
import time
import warnings
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 屏蔽新版 SDK 在使用思考模型时抛出的 thought_signature 拼接警告
warnings.filterwarnings("ignore", module="google.genai")

load_dotenv()

# ==========================================
# 1. 配置区
# ==========================================
# 使用你指定的模型
CONFIG = {
    "MODEL_NAME": "gemini-3.1-flash-lite-preview", 
    "RPM_LIMIT": 15,
    "BATCH_PLANETS": 4,  
    "CACHE_FILE": "translation_cache_gemini.json",
    "NAMES_JSON": "planet-name.json"
}

TARGET_TAGS = ["description", "spaceport"]

# ==========================================
# 2. 翻译引擎 (支持思维链模型适配)
# ==========================================
class GeminiPlanetEngine:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        self.system_instruction = (
            "你是一名专业的科幻游戏汉化专家。你将收到星球数据（包含名称及其标准中文译名，以及星球描述和太空港的描述）。\n"
            "要求：\n"
            "1. 请高质量汉化 description 和 spaceport。\n"
            "2. 风格：硬科幻、庄重、优美。\n"
            "3. 译名一致性：在描述中提到该星球时，必须使用提供的中文译名。\n"
            "4. 占位符：严禁修改 %ID_N% 格式的占位符。\n"
            "5. 格式：严格以 JSON 数组形式返回译文内容，不要在 JSON 外添加任何多余文字。"
        )
        self.logic_pattern = re.compile(r'(<[^>]+>|&\[[^\]]+\])')
        self.last_req_time = 0

    def translate_blocks(self, planet_batch):
        if not planet_batch: return []

        # 频率控制 (RPM=15 -> 每 4 秒一次，这里留足 5 秒安全余量)
        elapsed = time.time() - self.last_req_time
        wait_time = max(0, 7.5 - elapsed) 
        if wait_time > 0:
            time.sleep(wait_time)

        request_payload = []
        for p in planet_batch:
            planet_data = {
                "original_name": p['name'],
                "standard_translation": p['translation'],
                "to_translate": []
            }
            
            for t in p['texts']:
                placeholders = self.logic_pattern.findall(t)
                temp_text = t
                for i, ph in enumerate(placeholders):
                    temp_text = temp_text.replace(ph, f" %ID_{i}% ", 1)
                planet_data["to_translate"].append(temp_text)
            
            request_payload.append(planet_data)

        # 强约束 JSON 格式
        prompt = f"请参考译名表，汉化以下数据中的 'to_translate' 列表。\n" \
                 f"要求：将结果包裹在 ```json 和 ``` 之间，保持与原数组结构一致。\n\n" \
                 f"数据：\n{json.dumps(request_payload, ensure_ascii=False)}"
        
        try:
            response = self.client.models.generate_content(
                model=CONFIG["MODEL_NAME"],
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.1
                    # 故意移除了 response_mime_type，因为思考模型有时会与之冲突
                )
            )
            self.last_req_time = time.time()
            res_text = response.text
            
            # --- 核心修复：绕过 Thought 块，精准提取 JSON ---
            json_str = ""
            # 1. 优先尝试提取 Markdown 代码块中的 JSON
            code_block_match = re.search(r'```(?:json)?\s*(\[\s*\{.*?\}\s*\])\s*```', res_text, re.DOTALL)
            if code_block_match:
                json_str = code_block_match.group(1)
            else:
                # 2. 退而求其次，直接寻找包含数组的 JSON 括号
                array_match = re.search(r'\[\s*\{.*?\}\s*\]', res_text, re.DOTALL)
                if array_match:
                    json_str = array_match.group(0)

            if not json_str:
                print(f"\n[!] 无法从响应中提取 JSON，模型返回的末尾内容为: {res_text[-200:]}")
                return [None] * len(planet_batch)
                
            translated_data = json.loads(json_str)

            # --- 占位符还原与容错 ---
            final_output = []
            for i, p_res in enumerate(translated_data):
                if i >= len(planet_batch): break # 防止模型乱加数据
                
                p_final_texts = []
                current_ph_maps = planet_batch[i]['ph_maps']
                
                res_list = p_res.get("to_translate", p_res.get("content", []))
                
                if len(res_list) != len(current_ph_maps):
                    print(f"\n[!] 警告: 星球 {p_res.get('original_name')} 翻译文本数量不对齐，已跳过。")
                    final_output.append(None)
                    continue

                for j, translated_text in enumerate(res_list):
                    ph_list = current_ph_maps[j]
                    res_str = translated_text
                    for idx, ph in enumerate(ph_list):
                        pattern = rf'%\s*(?:ID|id|Id)\s*_{{0,1}}\s*{idx}\s*%'
                        res_str = re.sub(pattern, ph, res_str)
                    p_final_texts.append(res_str)
                final_output.append(p_final_texts)
            
            return final_output

        except Exception as e:
            print(f"\n[!] API请求或解析异常: {e}")
            return [None] * len(planet_batch)

# ==========================================
# 3. 文件处理器 (带详细统计)
# ==========================================
class PlanetFileProcessor:
    def __init__(self):
        self.engine = GeminiPlanetEngine()
        self.stats = {"reused": 0, "new_translated": 0, "errors": 0, "total_requests": 0}
        self.cache = self._load_json(CONFIG["CACHE_FILE"])
        self.names_glossary = self._load_json(CONFIG["NAMES_JSON"])
        self.planet_regex = re.compile(r'^planet\s+["`]{0,1}(.+?)["`]{0,1}\s*$')
        self.tag_regex = re.compile(rf'^(\s*)({"|".join(TARGET_TAGS)})\s+([\"`])(.+)([\"`])\s*$')

    def _load_json(self, path):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[!] 警告: 读取 {path} 失败 ({e})，将使用空字典。")
        return {}

    def _save_cache(self):
        with open(CONFIG["CACHE_FILE"], 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def process(self, input_file, output_file):
        self.start_time = time.time()
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        planets_blocks = []
        current_block = None
        
        print(f"[*] 载入译名表: {len(self.names_glossary)} 条 | 载入缓存: {len(self.cache)} 条")

        # 1. 结构扫描与缓存命中检查
        for idx, line in enumerate(lines):
            p_match = self.planet_regex.match(line.strip())
            if p_match:
                name = p_match.group(1)
                trans = self.names_glossary.get(name, name)
                current_block = {"name": name, "translation": trans, "pending": []}
                planets_blocks.append(current_block)
            
            t_match = self.tag_regex.match(line)
            if t_match and current_block:
                indent, tag, quote, content, eq = t_match.groups()
                h = hashlib.md5(content.encode()).hexdigest()
                
                # --- 缓存生效的核心逻辑 ---
                if h in self.cache:
                    self.stats["reused"] += 1
                    lines[idx] = f'{indent}{tag} {quote}{self.cache[h]}{eq}\n'
                else:
                    current_block["pending"].append({
                        "line_idx": idx, "content": content, "hash": h,
                        "tag": tag, "indent": indent, "quote": quote, "eq": eq
                    })

        to_translate = [b for b in planets_blocks if b["pending"]]
        total_blocks = len(to_translate)
        print(f"[*] 扫描完成。直接复用缓存: {self.stats['reused']} 行 | 待翻译星球: {total_blocks} 个")

        # 2. 批量翻译
        for i in range(0, total_blocks, CONFIG["BATCH_PLANETS"]):
            batch = to_translate[i : i + CONFIG["BATCH_PLANETS"]]
            
            engine_input = []
            for b in batch:
                ph_maps = [self.engine.logic_pattern.findall(item["content"]) for item in b["pending"]]
                engine_input.append({
                    "name": b["name"],
                    "translation": b["translation"],
                    "texts": [item["content"] for item in b["pending"]],
                    "ph_maps": ph_maps
                })

            names_str = ", ".join([x['name'] for x in engine_input])
            print(f"[*] ({i+len(batch)}/{total_blocks}) 正在请求 API: {names_str}")
            
            self.stats["total_requests"] += 1
            batch_results = self.engine.translate_blocks(engine_input)

            # 3. 写回内存并落盘 Cache
            for b_idx, p_translations in enumerate(batch_results):
                if p_translations:
                    for item_idx, trans_text in enumerate(p_translations):
                        item = batch[b_idx]["pending"][item_idx]
                        self.cache[item["hash"]] = trans_text
                        lines[item["line_idx"]] = f'{item["indent"]}{item["tag"]} {item["quote"]}{trans_text}{item["eq"]}\n'
                        self.stats["new_translated"] += 1
                else:
                    # 如果返回 None，说明解析失败，记入错误
                    self.stats["errors"] += len(batch[b_idx]["pending"])
            
            self._save_cache()

        # 4. 输出
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        self._print_final_report()

    def _print_final_report(self):
        total_time = time.time() - self.start_time
        st = self.stats
        req_per_sec = st['total_requests'] / total_time if total_time > 0 else 0
        print(f"\n" + "="*40)
        print(f"任务结束 | 耗时: {total_time:.1f}s | 速度: {req_per_sec*60:.2f} req/min")
        print(f"新增:{st['new_translated']} | 复用:{st['reused']} | 失败:{st['errors']}")
        print("="*40)

if __name__ == "__main__":
    processor = PlanetFileProcessor()
    # 执行处理
    processor.process("data/map planets.txt", "zh_cn_gemini/map planets.txt")