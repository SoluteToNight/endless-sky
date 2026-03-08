import os
import re
import json
import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator as GoogleEngine
from dotenv import load_dotenv

load_dotenv()

# --- 配置区 ---
CACHE_FILE = "translation_cache_google_v2.json"
GLOSSARY = {
    "Outfit": "装备", "Hull": "船体", "Shield": "护盾", 
    "Republic": "共和国", "Syndicate": "辛迪加", "Free Worlds": "自由世界",
    "Remnant": "遗民", "Alphas": "阿尔法", "Betas": "贝塔",
    "Navy": "海军", "Ember Waste": "灰烬荒原", "Graveyard": "坟场",
    "Tangled Shroud": "纠缠星云", "Quantum Keystone": "量子基石",
    "Hai": "亥族", "Korath": "科拉特", "Wanderer": "漫游者",
    "Coalition": "联合体", "Heliarchy": "日政司", "Quarg": "夸格",
    "Pug": "帕格", "Drak": "德拉克", "Successors": "传承者",
    "Predecessors": "前代者", "High Houses": "高庭世家",
    "Rulei": "鲁雷", "Precursors": "先行者", "Solemnity": "肃穆号"
}

TARGET_TAGS = ["display name", "description", "name", "spaceport", "dialog", "choice", "conversation", "landing message", "tip", "help"]
CREATIVE_BLOCKS = {"conversation", "dialog", "choice", "tip", "help"}

class EndlessSkyTranslator:
    def __init__(self):
        self.cache = self.load_cache()
        self.cache_lock = threading.Lock()
        self.stats = {"reused": 0, "new_translated": 0, "errors": 0, "total_requests": 0}
        self.start_time = None
        self.is_running = False
        
        # 保护游戏语法：<...> 或 &[...]
        self.logic_pattern = re.compile(r'(<[^>]+>|&\[[^\]]+\])')
        tags_pattern = "|".join([re.escape(t) for t in TARGET_TAGS])
        # 匹配单行 tag "content"
        self.tag_regex = re.compile(rf'^(\s*)({tags_pattern})\s+([\"`])(.+)([\"`])\s*$')
        # 匹配缩进的多行内容 `content`
        self.multi_line_regex = re.compile(r'^(\s+)([\"`])(.+)([\"`])\s*$')
        # 匹配块级关键字（如 conversation / variant / fleet）
        self.block_regex = re.compile(r'^([A-Za-z_][\w-]*)\b')

    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f: return json.load(f)
            except: return {}
        return {}

    def save_cache(self):
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _periodic_report(self):
        while self.is_running:
            time.sleep(10)
            if not self.is_running: break
            elapsed = time.time() - self.start_time
            with self.cache_lock:
                req_count = self.stats["total_requests"]
                speed = req_count / elapsed if elapsed > 0 else 0
                print(f"\n[监控汇报] 运行:{int(elapsed)}s | 速度:{speed:.2f} req/s | 已汉化:{self.stats['new_translated']}")

    def translate_via_google(self, text):
        if not text.strip(): return text
        with self.cache_lock: self.stats["total_requests"] += 1
        
        # 1. 占位符脱敏
        placeholders = self.logic_pattern.findall(text)
        temp_text = text
        for i, p in enumerate(placeholders):
            temp_text = temp_text.replace(p, f" %ID_{i}% ", 1)

        try:
            translator = GoogleEngine(source='en', target='zh-CN')
            res = translator.translate(temp_text)
            
            # 2. 术语库校正
            for eng, chs in GLOSSARY.items():
                res = re.compile(re.escape(eng), re.IGNORECASE).sub(chs, res)

            # 3. 强力占位符还原
            for i, p in enumerate(placeholders):
                pattern = rf'%\s*(?:ID|id|Id)\s*_{{0,1}}\s*{i}\s*%'
                res = re.sub(pattern, p, res)
            
            return re.sub(r'\s{2,}', ' ', res).strip()
        except:
            with self.cache_lock: self.stats["errors"] += 1
            return None

    def process_line(self, line_data):
        line, is_creative = line_data
        if "phrase" in line: return line

        # 尝试匹配单行标签格式
        m = self.tag_regex.match(line)
        if m:
            indent, tag, quote, content, eq = m.groups()
            return self._handle_logic(indent, tag, quote, content, eq, is_creative)
        
        # 尝试匹配缩进内容格式 (适用于 tip 下方的反引号文本)
        m_multi = self.multi_line_regex.match(line)
        if m_multi:
            indent, quote, content, eq = m_multi.groups()
            # 仅翻译 creative 语境下的反引号文本，避免误翻译 ship/system/outfit ID。
            if is_creative and quote == "`":
                return self._handle_logic(indent, "", quote, content, eq, is_creative)
        return line

    def _handle_logic(self, indent, tag, quote, content, eq, is_creative):
        if len(content.strip()) < 2: return f'{indent}{tag + " " if tag else ""}{quote}{content}{eq}\n'
        h = hashlib.md5(content.encode()).hexdigest()
        tag_prefix = f"{tag} " if tag else ""
        
        if h in self.cache:
            with self.cache_lock: self.stats["reused"] += 1
            return f'{indent}{tag_prefix}{quote}{self.cache[h]}{eq}\n'
        
        res = self.translate_via_google(content)
        if res:
            with self.cache_lock:
                self.cache[h] = res
                self.save_cache()
                self.stats["new_translated"] += 1
            return f'{indent}{tag_prefix}{quote}{res}{eq}\n'
        return f'{indent}{tag_prefix}{quote}{content}{eq}\n'

    def run(self, in_p, out_p):
        self.start_time = time.time()
        self.is_running = True
        threading.Thread(target=self._periodic_report, daemon=True).start()
        
        try:
            tasks = []
            if os.path.isfile(in_p): tasks.append((in_p, out_p))
            else:
                for root, _, files in os.walk(in_p):
                    for f in files:
                        if f.endswith(".txt"):
                            inf = os.path.join(root, f)
                            outf = os.path.join(out_p, os.path.relpath(inf, in_p))
                            tasks.append((inf, outf))

            for inf, outf in tasks:
                os.makedirs(os.path.dirname(outf), exist_ok=True)
                with open(inf, 'r', encoding='utf-8') as f: lines = f.readlines()
                
                line_contexts, active_indents = [], []
                for line in lines:
                    stripped = line.lstrip('\t ')
                    curr_indent = len(line) - len(stripped)
                    while active_indents and curr_indent <= active_indents[-1]:
                        if not stripped: break
                        active_indents.pop()
                    is_creative = len(active_indents) > 0
                    line_contexts.append((line, is_creative))
                    # 仅将明确文本块标记为 creative 语境。
                    block_match = self.block_regex.match(stripped)
                    if block_match and block_match.group(1) in CREATIVE_BLOCKS:
                        active_indents.append(curr_indent)

                with ThreadPoolExecutor(max_workers=6) as exe:
                    results = list(exe.map(self.process_line, line_contexts))
                
                with open(outf, 'w', encoding='utf-8') as f: f.writelines(results)
        finally:
            self.is_running = False
            total = time.time() - self.start_time
            print(f"\n任务结束 | 耗时:{total:.1f}s | 速度:{self.stats['total_requests']/total:.2f}req/s")

if __name__ == "__main__":
    translator = EndlessSkyTranslator()
    translator.run("data/human", "zh_cn_google/human")
