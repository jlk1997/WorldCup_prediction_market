import json
import urllib.request
import os

def collect_data():
    print("正在收集 2022 年世界杯公开比赛数据与球队数据...")
    
    # 1. 获取所有比赛详细数据 (包含比分、进球时间等)
    matches_url = 'https://raw.githubusercontent.com/openfootball/worldcup.json/master/2022/worldcup.json'
    try:
        req = urllib.request.Request(matches_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            matches_data = json.loads(response.read())
            
        with open('worldcup_2022_matches.json', 'w', encoding='utf-8') as f:
            json.dump(matches_data, f, ensure_ascii=False, indent=2)
        print("比赛数据收集完成！已保存为 worldcup_2022_matches.json")
    except Exception as e:
        print(f"比赛数据收集失败: {e}")

    # 2. 获取所有参赛球队与球员名单
    teams_url = 'https://raw.githubusercontent.com/fishenal/worldCup2022Data/main/worldcup.json'
    squads_url = 'https://raw.githubusercontent.com/fishenal/worldCup2022Data/main/solvedData/squadsData.json'
    
    try:
        req = urllib.request.Request(teams_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            teams_data = json.loads(response.read())
            
        req2 = urllib.request.Request(squads_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req2) as response:
            squads_data = json.loads(response.read())
            
        # 将两个数据整合到一个结构里
        combined_data = {
            "teams": teams_data,
            "squads": squads_data
        }
        
        with open('worldcup_2022_teams_players.json', 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
        print("球队和球员数据收集完成！已保存为 worldcup_2022_teams_players.json")
    except Exception as e:
        print(f"球队和球员数据收集失败: {e}")

if __name__ == "__main__":
    collect_data()
