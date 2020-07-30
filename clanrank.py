import requests,json,time,os
from hoshino import util,Service
from hoshino.util import FreqLimiter
import nonebot,hoshino
from hoshino.typing import CQEvent,CommandSession
from aiocqhttp.exceptions import Error as CQHttpError
sv_query = Service("clanrank-query",enable_on_default=True,visible = False,help_='''
【公会排名XXX】查询公会名包含XXX的公会
【会长排名XXX】查询会长名字包含XXX的公会
【查看排名114】查询排名为114的公会的信息
'''.strip())

sv_push = Service("clanrank-push",enable_on_default=True,visible=True,help_='''
【绑定公会ID】后跟会长ID来绑定公会，公会战期间每日5:30会自动推送前一日排名
'''.strip())

url_first = "https://service-kjcbcnmw-1254119946.gz.apigw.tencentcs.com/"
headers = {"Custom-Source":"did","Content-Type": "application/json","Referer": "https://kengxxiao.github.io/Kyouka/"}

_time_limit = 120
_lmt = FreqLimiter(_time_limit)

def loadConfig():
    """
    返回json格式的config
    """
    if os.path.exists('./hoshino/modules/clanrank/clanrank.json'):
        with open("./hoshino/modules/clanrank/clanrank.json","r",encoding='utf-8') as dump_f:
            try:
                # 读取错误一般是人工改动了config并且导致json格式错误
                clanrank_config = json.load(dump_f)
            except:
                clanrank_config = {}
    else:
        clanrank_config = {}
    return clanrank_config

def saveConfig(config):
    """
    保存信息到clanrank.json
    """
    with open("./hoshino/modules/clanrank/clanrank.json","w",encoding='utf-8') as dump_f:
        json.dump(config,dump_f,indent=4,ensure_ascii=False)
 
def get_rank(info,info_type):
    """
    母函数，网络查询，返回原始json信息
    可以查询的信息包括会长名字、公会名、名次、分数、榜单前十、会长ID
    仅限前2W名和分数线公会\n
    """
    url = url_first + info_type
    url += '/'
    
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
    elif info_type == "fav":
        info = [info] # 转化为表
        content = json.dumps({"ids": info, "history": "0"})
    else:
        # 这都能填错?爪巴!
        return -1
    r = requests.post(url, data=content, headers=headers)
    r_dec = json.loads(r.text)
    return r_dec

def process(dec,conciseMode = False):
    """
    处理获得的json消息，转化为向Q群发送的消息
    conciseMode=True, 简洁模式
    """
    # 异常处理
    if dec['code'] != 0:
        # Bad request
        msg = f"查询失败,错误代码{dec['code']},错误信息{dec['msg']}请联系维护人员"
        return msg
    result = len(dec['data'])
    if result == 0:
        msg += "没有查询结果,当前仅能查询前20000名公会,排名信息30分钟更新一次,相比于游戏内更新有10分钟左右延迟"
        return msg
    msg = ">>>公会战排名查询\n"

    # 此部分有问题，如果服务器时区不为东8区会出现错误时间转换
    queryTime = time.localtime(dec['ts'])
    formatTime = time.strftime('%Y-%m-%d %H:%M', queryTime)
    msg += f'数据更新时间{formatTime}\n'


    for i in range(result):
        clanname = dec['data'][i]['clan_name']
        rank = dec['data'][i]['rank']
        damage = dec['data'][i]['damage']
        leader = dec['data'][i]['leader_name']
        num = dec['data'][i]['member_num']
        if conciseMode == True:
            # 简洁模式
            msg_new = f"第{i+1}条:\n公会名：{clanname}\n排名：{rank}\n"
        else:
            msg_new = f"第{i+1}条信息:\n公会名称：{clanname}\n会长：{leader}\n成员数量：{num}\n目前排名：{rank}\n造成伤害：{damage}\n"
        msg += msg_new
    return msg

def set_clanname(group_id,leader_id):
    """
    为一个群绑定公会信息，由于公会是以会长ID为唯一标志的，因此传入参数只有群号，会长ID，请确保公会是前2W名
    """
    try:
        origin_info = get_rank(leader_id,"fav")
    except:
        # 网络错误
        return 1
    if origin_info['code'] != 0:
        # Bad request
        return origin_info['code']
    result = len(origin_info['data'])
    if result == 0:
        # 没有信息
        return 404
    clanName = origin_info['data'][0]['clan_name']
    leaderName = origin_info['data'][0]['leader_name']
    leaderId = leader_id

    clanrank_config = loadConfig()
    clan_info = {"clanName":clanName,"leaderName":leaderName,"leaderId":leaderId,"lastQuery":origin_info}
    clanrank_config[str(group_id)] = clan_info
    #print(clanrank_config)
    saveConfig(clanrank_config)
    return 0

@sv_push.on_fullmatch(('公会排名','工会排名'))
async def clanrankQuery(bot, ev:CQEvent):
    """
    查询本公会排名，需要预先绑定公会。
    只能查询已经绑定的公会信息！
    """
    # 检测有无绑定信息
    group_id = ev.group_id
    config = loadConfig()
    if str(group_id) not in config:
        msg = "未绑定公会信息，请发送【绑定公会+会长ID】来绑定公会信息"
        await bot.send(ev, msg, at_sender=True)
        return
    # 获取上次更新时间,假定网站更新比游戏内延迟12分钟
    lastQuertTime = config[str(group_id)]["lastQuery"]["ts"]
    if time.time() - lastQuertTime >= 42*60:
        # 上次查询时间戳有效时间42分钟,超时会触发联网查询
        msg = '缓存数据已超时，正在在线查询......\n'
        await bot.send(ev, msg)
        code = set_clanname(int(group_id),config[str(group_id)]["leaderId"])
        if code != 0:
            msg = f'发生错误{code}，可能的原因：公会更换了会长/工会排名不在前2W名。\n如果非上述原因，请联系维护并提供此信息'
            await bot.send(ev, msg)
            return
        else:
            config = loadConfig() # 信息已经被缓存，重新读取
    last_query_info = config[str(group_id)]["lastQuery"]
    msg = process(last_query_info)
    await bot.send(ev, msg)
    

@sv_push.on_prefix(['绑定公会','绑定工会'])
async def set_clan(bot,ev:CQEvent):
    """
    为一个公会绑定信息，需要会长ID
    """
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.send(ev, '您操作得太快了，请稍等一会儿', at_sender=True)
        return
    group_id = ev.group_id
    leader_id = ev.message.extract_plain_text()
    if not leader_id.isdigit():
        await bot.send(ev, '请正确输入会长ID', at_sender=True)
        return
    code = set_clanname(int(group_id),int(leader_id))
    if code != 0:
        msg = f'发生错误{code}，可能的原因：网络错误/ID输入错误/工会排名不在前2W名。\n如果非上述原因，请联系维护并提供此信息'
        await bot.send(ev, msg, at_sender=True)
        return
    msg = f"绑定成功\n"
    await bot.send(ev, msg)
    # 发送绑定过程中的查询结果
    clanrank_config = loadConfig()
    last_query_info = clanrank_config[str(group_id)]["lastQuery"]
    msg = process(last_query_info)
    await bot.send(ev, msg, at_sender=False)  

@sv_push.scheduled_job('cron',hour='5',minute='30')
async def clanrank_push_cn():
    bot = nonebot.get_bot()
    config = loadConfig()
    for g_id in config:
        msg = ''
        try:
            origin_info = get_rank(config[g_id]["leaderId"],"fav")
        except:
            # 网络错误
            msg += "查询本日5时公会战信息时发生错误"
        result = len(origin_info['data'])
        if origin_info['code'] != 0:
            # Bad request
            msg += "查询本日5时公会战信息时发生错误"
        elif result == 0:
            # 没有信息
            msg += "没有查询到本日5时的公会战排名信息"
        else:
            clanname = origin_info['data'][0]['clan_name']
            rank = origin_info['data'][0]['rank']
            msg += f'本日5时的公会战排名：\n公会名：{clanname}\n排名：{rank}'
        try:
            await bot.send_group_msg(group_id=int(g_id), message = msg)
            hoshino.logger.info(f'群{g_id} 推送排名成功')
        except CQHttpError as cqe:
            hoshino.logger.info(f'群{g_id} 推送排名错误：{type(cqe)}')
        

# -----------------------------------
# 此部分以下为旧版直接查询的函数

@sv_query.on_prefix(['查询公会', '查询工会'])
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
    info = get_rank(clan_name, "name")
    msg = process(info)
    msg += f"查询有{_time_limit}秒冷却"
    await bot.send(ev, msg)


@sv_query.on_prefix('查询会长')
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
    info = get_rank(leader_name, "leader")
    msg = process(info)
    msg += f"查询有{_time_limit}秒冷却"
    await bot.send(ev, msg)


@sv_query.on_prefix('查询排名')
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
    info = get_rank(rank, "rank")
    msg = process(info)
    msg += f"查询有{_time_limit}秒冷却"
    await bot.send(ev, msg)