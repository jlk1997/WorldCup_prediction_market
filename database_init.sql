-- 球队信息表
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,          -- 球队名称，如：阿根廷
    country_code VARCHAR(10) NOT NULL,          -- 国家代码，如：ARG
    fifa_ranking INTEGER,                       -- FIFA世界排名
    group_name VARCHAR(10),                     -- 所在小组，如：A组
    coach VARCHAR(100),                         -- 主教练
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 球员信息表
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE, -- 所属球队
    name VARCHAR(100) NOT NULL,                 -- 球员姓名
    position VARCHAR(50) NOT NULL,              -- 场上位置 (前锋, 中场, 后卫, 门将)
    age INTEGER,                                -- 年龄
    jersey_number INTEGER,                      -- 球衣号码
    is_key_player BOOLEAN DEFAULT FALSE,        -- 是否为核心球员
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 添加更新时间触发器功能
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为球队表添加触发器
DROP TRIGGER IF EXISTS update_teams_modtime ON teams;
CREATE TRIGGER update_teams_modtime
BEFORE UPDATE ON teams
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- 为球员表添加触发器
DROP TRIGGER IF EXISTS update_players_modtime ON players;
CREATE TRIGGER update_players_modtime
BEFORE UPDATE ON players
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();
