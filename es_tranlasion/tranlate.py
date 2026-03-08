import os
import re
import json
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
MODEL_NAME = "deepseek-chat"
CACHE_FILE = "translation_cache_v5.json"

# --- 根据 Wiki 描述修正的术语表 ---
GLOSSARY = {
    # 基础与人类势力 (Human Factions)
    "Outfit": "装备", "Hull": "船体", "Shield": "护盾", 
    "Republic": "共和国", 
    "Syndicate": "辛迪加", 
    "Free Worlds": "自由世界",
    "Merchants": "商贸团",
    "Pirates": "海盗",
    "Remnant": "遗民",          # 居住在灰烬荒原的高技术人类派系
    "The Deep": "深空域",        # 远离核心区的偏远人类星域
    
    # 人类基因工程产物 (Engineered Humans)
    "Alphas": "阿尔法",          # 基因改造的超级士兵
    "Betas": "贝塔",            # 基因改造的劳工阶层
    
    # 军事与情报机构 (Organizations)
    "Navy": "海军",              # 通常指共和国海军
    "Navy Intelligence": "海军情报局",
    "Republic Intelligence": "共和国情报局",
    "Deep Security": "深空安保",
    "Southern Mutual Defense Pact": "南方互保公约", # 自由世界的前身联盟
    
    # 地理与历史术语 (Lore & Regions)
    "Ember Waste": "灰烬荒原",   # 遗民所在地
    "Graveyard": "坟场",         # 位于银河西南部的危险区域
    "Tangled Shroud": "纠缠星云", # 传承者所在的区域
    "Unification War": "统一战争",
    "Quantum Keystone": "量子基石", # 穿越不稳定虫洞的关键设备
    
    # 核心外星文明 (Major Species)
    "Hai": "亥族",
    "Korath": "科拉特",
    "Kor Mereti": "科·梅雷蒂",
    "Kor Sestor": "科·塞斯托",
    "Wanderer": "漫游者",
    "Coalition": "联合体",
    "Heliarchy": "日政司",
    "Quarg": "夸格",
    "Pug": "帕格",
    "Drak": "德拉克",
    
    # 传承者相关 (Successors Lore)
    "Successors": "传承者",
    "Predecessors": "前代者",
    "High Houses": "高庭世家",
    "Old Houses": "旧世家",
    "New Houses": "新世家",
    "People's Houses": "庶民院",
    
    # 古代与新兴势力 (Ancient & Minor)
    "Rulei": "鲁雷",
    "Precursors": "先行者",
    "Solemnity": "肃穆号",
    "Umbral Reach": "暗影领域",
    "Sheragi": "舍拉吉",
    "Gegno": "杰格诺",
    "Ka'het": "卡希特",
    "Aberrant": "异端",
    "Bunrodea": "邦罗迪亚",
    "Incipias": "因希比亚",
    "Avgi": "阿维吉"
}

TARGET_TAGS = ["display name", "description", "category", "name", "spaceport", "dialog", "landing message", "tip", "help"]

class RobustTranslator:
    def __init__(self):
        self.cache = self.load_cache()
        self.cache_lock = threading.Lock()
        self.logic_pattern = re.compile(r'(<[^>]+>|&\[[^\]]+\])')
        tags_pattern = "|".join([re.escape(t) for t in TARGET_TAGS])
        self.tag_regex = re.compile(rf'^(\s*)({tags_pattern})\s+([\"`])(.+)([\"`])\s*$')

    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f: return json.load(f)
            except: return {}
        return {}

    def save_cache(self):
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def translate_via_api(self, text, tag):
        if not text.strip(): return text
        
        # 1. 占位符替换 (Escaping)
        placeholders = self.logic_pattern.findall(text)
        temp_text = text
        for i, p in enumerate(placeholders):
            temp_text = temp_text.replace(p, f" [[[BLOCK_{i}]]] ", 1)

        glossary_str = ", ".join([f"{k}->{v}" for k, v in GLOSSARY.items()])
        try:
            prompt = (
                f"你是一个专业的科幻游戏汉化专家。请翻译《Endless Sky》中的{tag}内容。\n"
                f"【术语库】：{glossary_str}\n"
                f"【极其重要】：严禁翻译或修改 [[[BLOCK_N]]] 标记，它们代表代码。请保持其在句子中的语义位置。\n"
                f"待翻译文本: {temp_text}"
            )
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": "你是一名精通太空歌剧风格的翻译官，翻译需严谨且富有科幻感。"},
                          {"role": "user", "content": prompt}],
                temperature=0.1
            )
            res = response.choices[0].message.content.strip().strip('"').strip('`')

            # 2. 占位符还原 (Restoring)
            for i, p in enumerate(placeholders):
                res = re.sub(rf'\[\[\[\s*BLOCK_{i}\s*\]\]\]', p, res)
            return re.sub(r'\s{2,}', ' ', res).strip()
        except Exception: return None

    def process_line(self, line):
        m = self.tag_regex.match(line)
        if m:
            indent, tag, quote, content, eq = m.groups()
            h = hashlib.md5(content.encode()).hexdigest()
            if h in self.cache: return f'{indent}{tag} {quote}{self.cache[h]}{eq}\n'
            res = self.translate_via_api(content, tag)
            if res:
                with self.cache_lock:
                    self.cache[h] = res
                    self.save_cache()
                return f'{indent}{tag} {quote}{res}{eq}\n'
        return line

    def run(self, in_p, out_p):
        for root, _, files in os.walk(in_p):
            for file in files:
                if file.endswith(".txt"):
                    inf = os.path.join(root, file)
                    outf = os.path.join(out_p, os.path.relpath(inf, in_p))
                    os.makedirs(os.path.dirname(outf), exist_ok=True)
                    with open(inf, 'r', encoding='utf-8') as f: lines = f.readlines()
                    with ThreadPoolExecutor(max_workers=8) as exe:
                        results = list(exe.map(self.process_line, lines))
                    with open(outf, 'w', encoding='utf-8') as f: f.writelines(results)

if __name__ == "__main__":
    translator = RobustTranslator()
    translator.run("data", "zh_cn")