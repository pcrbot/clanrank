import math

bossData = {
    'scoreRate': [
        [1, 1, 1.3, 1.3, 1.5],
        [1.4, 1.4, 1.8, 1.8, 2],
        [2.0, 2.0, 2.5, 2.5, 3]
    ],
    'hp': [
        [6000000, 8000000, 10000000, 12000000, 20000000],
        [6000000, 8000000, 10000000, 12000000, 20000000],
        [6000000, 8000000, 10000000, 12000000, 20000000]
    ],
    # 标记每个阶段的最大周目数（累计周目）
    "cy": [3, 10]
}

def calc_hp(score: int):
    # 输出时应当全部加1
    king = 0
    cycle = 0
    stage = 0
    max_stage = len(bossData["cy"])
    score_left = score

    hp_max = bossData["hp"][stage][king]
    rate = bossData["scoreRate"][stage][king]
    # 当剩余分数大于当前BOSS分数时循环
    while score_left > hp_max*rate:


        # 获取当前BOSS的倍率和最大血量
        rate = bossData["scoreRate"][stage][king]
        hp_max = bossData["hp"][stage][king]

        # 计算剩余血量
        score_left = score_left - rate * hp_max

        # 修改BOSS编号，检查是否进入下一周目
        if king >=  4:
            king = 0
            cycle = cycle + 1
        else:
            king = king + 1
        # 检查周目数，是否进入下一阶段
        if stage < max_stage:
            if  cycle > bossData["cy"][stage] - 1:
                stage = stage + 1

        rate = bossData["scoreRate"][stage][king]
        hp_max = bossData["hp"][stage][king]
    
    # 最后剩余分数按照比率转化为血量

    hp_left = hp_max - score_left / rate
    return f'{cycle+1}周目{king+1}王 [{math.floor(hp_left)}/{hp_max}]'

