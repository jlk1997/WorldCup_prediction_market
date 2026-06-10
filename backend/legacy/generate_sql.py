import json
import urllib.request
from datetime import datetime

def generate_sql():
    # 数据来源：GitHub 上的 2022 世界杯开源数据
    teams_url = 'https://raw.githubusercontent.com/fishenal/worldCup2022Data/main/worldcup.json'
    squads_url = 'https://raw.githubusercontent.com/fishenal/worldCup2022Data/main/solvedData/squadsData.json'
    
    print("正在拉取球队数据...")
    req = urllib.request.Request(teams_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        teams_data = json.loads(response.read())
        
    print("正在拉取球员数据...")
    req2 = urllib.request.Request(squads_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req2) as response:
        squads_data = json.loads(response.read())

    # 一些基础的排名和分组映射（这里作为数据补充，2022世界杯）
    team_extra_info = {
        'QAT': {'group': 'A', 'fifa': 50, 'coach': 'Félix Sánchez'},
        'ECU': {'group': 'A', 'fifa': 44, 'coach': 'Gustavo Alfaro'},
        'SEN': {'group': 'A', 'fifa': 18, 'coach': 'Aliou Cissé'},
        'NED': {'group': 'A', 'fifa': 8, 'coach': 'Louis van Gaal'},
        'ENG': {'group': 'B', 'fifa': 5, 'coach': 'Gareth Southgate'},
        'IRN': {'group': 'B', 'fifa': 20, 'coach': 'Carlos Queiroz'},
        'USA': {'group': 'B', 'fifa': 16, 'coach': 'Gregg Berhalter'},
        'WAL': {'group': 'B', 'fifa': 19, 'coach': 'Rob Page'},
        'ARG': {'group': 'C', 'fifa': 3, 'coach': 'Lionel Scaloni'},
        'KSA': {'group': 'C', 'fifa': 51, 'coach': 'Hervé Renard'},
        'MEX': {'group': 'C', 'fifa': 13, 'coach': 'Gerardo Martino'},
        'POL': {'group': 'C', 'fifa': 26, 'coach': 'Czesław Michniewicz'},
        'FRA': {'group': 'D', 'fifa': 4, 'coach': 'Didier Deschamps'},
        'AUS': {'group': 'D', 'fifa': 38, 'coach': 'Graham Arnold'},
        'DEN': {'group': 'D', 'fifa': 10, 'coach': 'Kasper Hjulmand'},
        'TUN': {'group': 'D', 'fifa': 30, 'coach': 'Jalel Kadri'},
        'ESP': {'group': 'E', 'fifa': 7, 'coach': 'Luis Enrique'},
        'CRC': {'group': 'E', 'fifa': 31, 'coach': 'Luis Fernando Suárez'},
        'GER': {'group': 'E', 'fifa': 11, 'coach': 'Hansi Flick'},
        'JPN': {'group': 'E', 'fifa': 24, 'coach': 'Hajime Moriyasu'},
        'BEL': {'group': 'F', 'fifa': 2, 'coach': 'Roberto Martínez'},
        'CAN': {'group': 'F', 'fifa': 41, 'coach': 'John Herdman'},
        'MAR': {'group': 'F', 'fifa': 22, 'coach': 'Walid Regragui'},
        'CRO': {'group': 'F', 'fifa': 12, 'coach': 'Zlatko Dalić'},
        'BRA': {'group': 'G', 'fifa': 1, 'coach': 'Tite'},
        'SRB': {'group': 'G', 'fifa': 21, 'coach': 'Dragan Stojković'},
        'SUI': {'group': 'G', 'fifa': 15, 'coach': 'Murat Yakin'},
        'CMR': {'group': 'G', 'fifa': 43, 'coach': 'Rigobert Song'},
        'POR': {'group': 'H', 'fifa': 9, 'coach': 'Fernando Santos'},
        'GHA': {'group': 'H', 'fifa': 22, 'coach': 'Otto Addo'},
        'URU': {'group': 'H', 'fifa': 14, 'coach': 'Diego Alonso'},
        'KOR': {'group': 'H', 'fifa': 28, 'coach': 'Paulo Bento'}
    }

    sql_statements = []
    sql_statements.append("TRUNCATE TABLE players RESTART IDENTITY CASCADE;")
    sql_statements.append("TRUNCATE TABLE teams RESTART IDENTITY CASCADE;\n")

    team_id_map = {}
    team_id_counter = 1

    print("正在生成 SQL 脚本...")
    # 插入球队
    for country_code, players in squads_data.items():
        # 匹配球队名字
        team_name = country_code
        for t in teams_data:
            if t.get('IdCountry') == country_code:
                names = t.get('TeamName')
                if isinstance(names, list) and len(names) > 0:
                    team_name = names[0].get('Description', country_code)
                elif isinstance(names, str):
                    team_name = names
                break
        
        team_name = team_name.replace("'", "''")
        extra = team_extra_info.get(country_code, {'group': '未知', 'fifa': 99, 'coach': '未知'})
        
        sql = f"INSERT INTO teams (id, name, country_code, fifa_ranking, group_name, coach) VALUES ({team_id_counter}, '{team_name}', '{country_code}', {extra['fifa']}, '{extra['group']}', '{extra['coach']}');"
        sql_statements.append(sql)
        team_id_map[country_code] = team_id_counter
        team_id_counter += 1

    sql_statements.append("\n")

    # 插入球员
    for country_code, players in squads_data.items():
        team_id = team_id_map.get(country_code)
        if not team_id:
            continue
            
        for p in players:
            name = p.get('name', '').replace("'", "''")
            position = p.get('position', 'Unknown')
            age = p.get('age', 25)
            jersey = p.get('jerseyNum', 0)
            
            # 简单的核心球员逻辑：10号或队长等（这里为了演示，随机挑一些号码或著名球员）
            is_key = 'TRUE' if jersey in [10, 9, 7] else 'FALSE'
            
            sql = f"INSERT INTO players (team_id, name, position, age, jersey_number, is_key_player) VALUES ({team_id}, '{name}', '{position}', {age}, {jersey}, {is_key});"
            sql_statements.append(sql)

    # 写入文件
    with open('../data_insert.sql', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_statements))
    
    print("生成完毕！文件保存在根目录下的 data_insert.sql")

if __name__ == "__main__":
    generate_sql()
