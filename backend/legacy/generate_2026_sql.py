import json

def generate_2026_sql():
    # 用户提供的 2026 分组数据
    groups_data = {
        'A': ['墨西哥', '南非', '韩国', '捷克'],
        'B': ['加拿大', '波黑', '卡塔尔', '瑞士'],
        'C': ['巴西', '摩洛哥', '海地', '苏格兰'],
        'D': ['美国', '巴拉圭', '澳大利亚', '土耳其'],
        'E': ['德国', '库拉索', '科特迪瓦', '厄瓜多尔'],
        'F': ['荷兰', '日本', '瑞典', '突尼斯'],
        'G': ['比利时', '埃及', '伊朗', '新西兰'],
        'H': ['西班牙', '佛得角', '沙特阿拉伯', '乌拉圭'],
        'I': ['法国', '塞内加尔', '伊拉克', '挪威'],
        'J': ['阿根廷', '阿尔及利亚', '奥地利', '约旦'],
        'K': ['葡萄牙', '刚果（金）', '乌兹别克斯坦', '哥伦比亚'],
        'L': ['英格兰', '克罗地亚', '加纳', '巴拿马']
    }

    # 为了保证表结构的完整性，我们给这些球队加上一些模拟的 FIFA 排名（排名越高实力越强）和国家代码
    # 实际开发中可以通过接口查真实排名，这里先保证系统能跑起来
    mock_rankings = {
        '阿根廷': 1, '法国': 2, '巴西': 3, '英格兰': 4, '比利时': 5, '葡萄牙': 6, '荷兰': 7, '西班牙': 8,
        '哥伦比亚': 12, '墨西哥': 15, '乌拉圭': 11, '瑞士': 19, '美国': 13, '德国': 16, '塞内加尔': 17, '日本': 18,
        '伊朗': 20, '韩国': 22, '澳大利亚': 23, '奥地利': 25, '瑞典': 26, '突尼斯': 28, '阿尔及利亚': 30, '埃及': 33,
        '土耳其': 35, '厄瓜多尔': 31, '苏格兰': 39, '波黑': 41, '捷克': 36, '加拿大': 48, '沙特阿拉伯': 53,
        '科特迪瓦': 49, '巴拉圭': 56, '南非': 58, '卡塔尔': 58, '加纳': 61, '伊拉克': 59, '乌兹别克斯坦': 66,
        '巴拿马': 44, '佛得角': 65, '约旦': 70, '海地': 90, '库拉索': 91, '新西兰': 104, '刚果（金）': 67,
        '克罗地亚': 10, '摩洛哥': 14, '挪威': 46
    }
    
    country_codes = {
        '阿根廷': 'ARG', '法国': 'FRA', '巴西': 'BRA', '英格兰': 'ENG', '比利时': 'BEL', '葡萄牙': 'POR', '荷兰': 'NED', '西班牙': 'ESP',
        '哥伦比亚': 'COL', '墨西哥': 'MEX', '乌拉圭': 'URU', '瑞士': 'SUI', '美国': 'USA', '德国': 'GER', '塞内加尔': 'SEN', '日本': 'JPN',
        '伊朗': 'IRN', '韩国': 'KOR', '澳大利亚': 'AUS', '奥地利': 'AUT', '瑞典': 'SWE', '突尼斯': 'TUN', '阿尔及利亚': 'ALG', '埃及': 'EGY',
        '土耳其': 'TUR', '厄瓜多尔': 'ECU', '苏格兰': 'SCO', '波黑': 'BIH', '捷克': 'CZE', '加拿大': 'CAN', '沙特阿拉伯': 'KSA',
        '科特迪瓦': 'CIV', '巴拉圭': 'PAR', '南非': 'RSA', '卡塔尔': 'QAT', '加纳': 'GHA', '伊拉克': 'IRQ', '乌兹别克斯坦': 'UZB',
        '巴拿马': 'PAN', '佛得角': 'CPV', '约旦': 'JOR', '海地': 'HAI', '库拉索': 'CUW', '新西兰': 'NZL', '刚果（金）': 'COD',
        '克罗地亚': 'CRO', '摩洛哥': 'MAR', '挪威': 'NOR'
    }

    sql_statements = []
    sql_statements.append("-- 2026年世界杯 48支球队初始化数据")
    sql_statements.append("TRUNCATE TABLE players RESTART IDENTITY CASCADE;")
    sql_statements.append("TRUNCATE TABLE teams RESTART IDENTITY CASCADE;\n")

    team_id = 1
    for group_name, teams in groups_data.items():
        for team_name in teams:
            code = country_codes.get(team_name, 'UNK')
            rank = mock_rankings.get(team_name, 99) # 找不到的默认给99名
            coach = '待定' # 2026名单尚未完全确定，先给待定
            
            sql = f"INSERT INTO teams (id, name, country_code, fifa_ranking, group_name, coach) VALUES ({team_id}, '{team_name}', '{code}', {rank}, '{group_name}', '{coach}');"
            sql_statements.append(sql)
            team_id += 1

    # 写入文件
    with open('../data_insert_2026.sql', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_statements))
    
    print("生成完毕！文件保存在根目录下的 data_insert_2026.sql")

if __name__ == "__main__":
    generate_2026_sql()
