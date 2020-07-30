import requests,json,time
from hoshino import util,Service
from hoshino.util import FreqLimiter
from hoshino.typing import CQEvent
sv = Service("clanrank",enable_on_default=True,visible = False)

url_first = "https://service-kjcbcnmw-1254119946.gz.apigw.tencentcs.com/"
_time_limit = 30
_lmt = FreqLimiter(_time_limit)

async def get_rank(info,info_type):
    """
    获取公会排名(25010之前),刷新时间为30分钟一次,相比于游戏内排名有约30分钟延迟\n
    info_type可能的值"leader"(按会长名),"name"(按公会名),"score"(按分数),"rank"(按排名)\n
    info是待搜索信息,不必填完整,可以以部分信息来搜索\n
    目前只能返回第一页数据,也就是前10个数据
    """
    url = url_first + info_type
    url += '/'
    headers = {"Custom-Source":"did","Content-Type": "application/json","Referer": "https://kengxxiao.github.io/Kyouka/"}
    
    if info_type == "name":
        url += '-1'
        content = json.dumps({"history":"0","clanName": info})
    elif info_type == "leader":
        url += '-1'
        content = json.dumps({"history":"0","leaderName": info})
    elif info_type == "score":
        # 无需额外请求头
        url += info
        content = json.dumps({"history":"0"})
    elif info_type == "rank":
        url += info
        content = json.dumps({"history":"0"})
    else:
        # 这都能填错?爪巴!
        msg = '内部错误，请联系维护人员'
        return msg
    r = requests.post(url, data=content, headers=headers)
    r_dec = json.loads(r.text)

    if r_dec['code'] != 0:
        # Bad request
        msg = f"查询失败,错误代码{r_dec['code']},错误信息{r_dec['msg']}请联系维护人员"
        return msg

    msg = ">>>公会战排名查询\n"
    queryTime = time.localtime(r_dec['ts'])
    formatTime = time.strftime('%Y-%m-%d %H:%M', queryTime)
    msg += f'数据更新时间{formatTime}\n'
    # 查询不到结果
    result = len(r_dec['data'])
    if result == 0:
        msg += "没有查询结果,当前仅能查询前25010名公会,排名信息30分钟更新一次,相比于游戏内更新有10分钟左右延迟"
        return msg
    for i in range(result):
        clanname = r_dec['data'][i]['clan_name']
        rank = r_dec['data'][i]['rank']
        damage = r_dec['data'][i]['damage']
        leader = r_dec['data'][i]['leader_name']
        num = r_dec['data'][i]['member_num']
        msg_new = f"第{i+1}条信息:\n公会名称：{clanname}\n会长：{leader}\n成员数量：{num}\n目前排名：{rank}\n造成伤害：{damage}\n\n"
        msg += msg_new
    return msg

@sv.on_prefix(['公会排名','工会排名'])
async def rank_query_by_name(bot, ev: CQEvent):
    """
    通过公会名查询排名
    """
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.send(ev, '您查询得太快了，请稍等一会儿', at_sender=True)
        return
    _lmt.start_cd(uid)
    clan_name = ev.message.extract_plain_text()
    msg = await get_rank(clan_name,"name")
    msg += f"查询有{_time_limit}秒冷却"
    await bot.send(ev,msg)

@sv.on_prefix('会长排名')
async def rank_query_by_leader(bot, ev: CQEvent):
    """
    通过会长名字查询排名
    """
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.send(ev, '您查询得太快了，请稍等一会儿', at_sender=True)
        return
    _lmt.start_cd(uid)
    leader_name = ev.message.extract_plain_text()
    msg = await get_rank(leader_name,"leader")
    msg += f"查询有{_time_limit}秒冷却"
    await bot.send(ev,msg)

@sv.on_prefix('查看排名')
async def rank_query_by_rank(bot, ev: CQEvent):
    """
    查看指定名次的公会信息
    """
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.send(ev, '您查询得太快了，请稍等一会儿', at_sender=True)
        return
    _lmt.start_cd(uid)
    rank = ev.message.extract_plain_text()
    if not rank.isdigit():
        await bot.send(ev, '请正确输入数字', at_sender=True)
        return
    msg = await get_rank(rank,"rank")
    msg += f"查询有{_time_limit}秒冷却"
    await bot.send(ev,msg)

@sv.on_prefix('分数排名')
async def rank_query_by_score(bot, ev: CQEvent):
    """
    查看指定分数的公会信息,只会返回当前分数最高排名的信息
    """
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.send(ev, '您查询得太快了，请稍等一会儿', at_sender=True)
        return
    _lmt.start_cd(uid)
    score = ev.message.extract_plain_text()
    if not score.isdigit():
        await bot.send(ev, '请正确输入数字', at_sender=True)
        return
    msg = await get_rank(score,"score")
    msg += f"只会返回当前分数最高排名公会的信息\n"
    msg += f"查询有{_time_limit}秒冷却"
    await bot.send(ev,msg) 