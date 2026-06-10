import re
import json

def parse_schedule():
    with open('../赛程', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取比赛信息正则，优化匹配逻辑
    # 示例: A组 (揭幕战)06月12日 (周五) 03:00墨西哥 🇲🇽 vs 南非 🇿🇦墨西哥城 · 阿兹特克体育场
    pattern = r'([A-L]组(?:\s*\(揭幕战\))?)(06月\d{2}日)\s*\([^\)]+\)\s*(\d{2}:\d{2})\s*([^\s]+?)\s*(?:[\U0001F1E6-\U0001F1FF]{2}|🏴)?\s*vs\s*([^\s]+?)\s*(?:[\U0001F1E6-\U0001F1FF]{2}|🏴)(.+?(?:体育场|体育馆|球场))'
    
    matches = re.finditer(pattern, content)
    schedule_data = []
    
    for match in matches:
        group = match.group(1).strip()
        date = match.group(2).strip()
        time = match.group(3).strip()
        team1 = match.group(4).strip()
        team2 = match.group(5).strip()
        stadium = match.group(6).strip()
        
        # 移除任何可能的残余国旗字符
        team1 = re.sub(r'[\U0001F1E6-\U0001F1FF🏴]', '', team1).strip()
        team2 = re.sub(r'[\U0001F1E6-\U0001F1FF🏴]', '', team2).strip()
        # 处理特殊情况 乌鲁木齐/乌拉圭
        if '乌拉圭' in team2:
            team2 = '乌拉圭'
        stadium = match.group(6).strip()
        
        schedule_data.append({
            "group": group,
            "date": f"2026年{date}",
            "time": time,
            "team1": team1,
            "team2": team2,
            "stadium": stadium,
            "status": "upcoming" # 默认未开始
        })
        
    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(schedule_data, f, ensure_ascii=False, indent=2)
    print(f"成功解析 {len(schedule_data)} 场比赛！")

if __name__ == '__main__':
    parse_schedule()