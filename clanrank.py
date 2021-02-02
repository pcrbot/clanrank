import json
import os
import re
import time
from datetime import timedelta

import hoshino
import nonebot
import requests
from aiocqhttp.exceptions import Error as CQHttpError
from hoshino import Service
from hoshino.config import SUPERUSERS
from hoshino.typing import CQEvent
from hoshino.util import FreqLimiter

from .boss import calc_hp
from .msg_temp import *

try:
    from hoshino.config import CONFIG_PATH
except ImportError:
    CONFIG_PATH = '~/.hoshino/'
from hoshino.priv import set_block_user

_help1 = '''
[查询公会XXX]查询公会名包含XXX的公会
[查询会长XXX]查询会长名字包含XXX的公会
[查询排名114]查询排名为114的公会的信息
[分数线]查询分数线
'''.strip()

_help2='''
以下仅限国服B站，渠道服/日台服均不可用
如果不知道会长ID可以先通过通用查询来查询会长的ID
[绑定公会+会长ID]后跟会长ID来绑定公会, 公会战期间每日5:30会自动推送前一日排名
[公会排名]查询本公会的排名(需绑定公会ID)
'''.strip()

sv_query = Service("公会战排名查询",enable_on_default=True,visible = True,help_=_help1,bundle='公会战')

sv_push = Service("公会战排名推送",enable_on_default=True,bundle='公会战',visible=True,help_=_help2)

url_first = "https://service-kjcbcnmw-1254119946.gz.apigw.tencentcs.com/"
headers = {"Custom-Source":"GitHub@var-mixer","Content-Type": "application/json","Referer": "https://kengxxiao.github.io/Kyouka/"}

_time_limit = 20
_lmt = FreqLimiter(_time_limit)

PATH = os.path.expanduser(CONFIG_PATH + 'clanrank/clanrank.json')
_dir = os.path.expanduser(CONFIG_PATH + 'clanrank')
if not os.path.exists(_dir):
    os.makedirs(_dir)

inject_regex = re.compile(r'\[CQ:(.*),(.*)\]')


async def notify_master(txt) -> bool:
    '''
    通知主人
    '''
    try:
        await nonebot.get_bot().send_private_msg(user_id=SUPERUSERS[0], message=txt)
    except nonebot.CQHttpError:
        return False
    return True



def loadConfig():
    """
    返回json格式的config
    """
    if os.path.exists(PATH):
        with open(PATH,"r",encoding='utf-8') as dump_f:
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
    with open(PATH,"w",encoding='utf-8') as dump_f:
        json.dump(config,dump_f,indent=4,ensure_ascii=False)
 

def get_rank(info, info_type, time=0):
    """
    母函数, 网络查询, 返回原始json信息
    可以查询的信息包括会长名字、公会名、名次、分数、榜单前十、会长ID
    仅限前2W名和分数线公会\n
    time请保证为时间戳形式
    """
    url = url_first + info_type
    url += '/'
    # 用🔨的正则，那是人用的？
    if info_type == "name":
        url += '-1'
        content = json.dumps({"history":int(time),"clanName": info})
    elif info_type == "leader":
        url += '-1'
        content = json.dumps({"history":int(time),"leaderName": info})
    elif info_type == "score":
        # 无需额外请求头
        url += info
        content = json.dumps({"history":int(time)})
    elif info_type == "rank":
        url += info
        content = json.dumps({"history":int(time)})
    elif info_type == "fav":
        info = [info] # 转化为表
        content = json.dumps({"ids": info, "history": int(time)})
    elif info_type == "line":
        # info内容此时无效
        content = json.dumps({"ids": info, "history": int(time)})
    else:
        # 这都能填错?爪巴!
        return -1
    try:
        r = requests.post(url, data=content, headers=headers,timeout=3)
    except:
        # timeout
        return 408
    r_dec = json.loads(r.text)
    hoshino.logger.info(f'接收到查询结果{r.text}')
    return r_dec


def process(dec, infoList:list):
    """
    处理获得的json消息, 转化为向Q群发送的消息\n
    infoList:需要显示的信息的列表，可以为以下元素：\n
    'clan_name':公会名称 \n
    'rank':公会排名 \n
    'damage':分数 \n
    'boss': BOSS进度\n
    'index':序号(多条信息时) \n
    'leader_name': 会长名 \n
    'member_num'：成员人数 \n
    'ts':时间戳(无转换) \n
    'leader_viewer_id':会长数字ID \n
    'full'：所有匹配到的查询结果
    """
    _infoList = infoList.copy()
    # 异常处理
    if dec['code'] != 0:
        # Bad request
        msg = f"查询失败,错误代码{dec['code']},错误信息{dec['msg']}请联系维护人员\n"
        return msg
    result = len(dec['data'])
    if result == 0:
        msg = "没有查询结果,仅能查询前20000名公会,排名信息30分钟更新一次,相比于游戏内更新有10分钟左右延迟\n"
        return msg

    # 预处理列表信息中的部分
    msg = ''
    if 'full' in _infoList:
        if dec['full'] != 0:
            msg += f"全部查询结果：{dec['full']}\n"
        if dec['full'] >= 10:
            msg += '查询结果较多，如果显示不全请前往网页查询\n'
        _infoList.remove('full')
    if 'ts' in _infoList:
        queryTime = time.localtime(dec['ts'])
        # 请预先调整机器时区为东8区，此处会使用系统默认时区
        formatTime = time.strftime('%Y-%m-%d %H:%M', queryTime)
        msg += f"更新时间{formatTime}\n"
        _infoList.remove('ts')
    if 'index' in _infoList:
        # 预处理，将index移动到第一位
        _infoList.remove('index')
        _infoList.insert(0,'index')

    for i in range(result):
        for key in _infoList:
            if key == 'index':
                msg += f'第{i+1}条信息：\n'
            elif key == 'boss':
                msg += f"{msg_dic[key]}："
                damage = dec['data'][i]['damage']
                msg += f"{calc_hp(damage)}\n"
            else:
                msg += f"{msg_dic[key]}："
                msg += f"{dec['data'][i][key]}\n"
        msg += '\n'
    return msg


def set_clanname(group_id,leader_id):
    """
    为一个群绑定公会信息, 由于公会是以会长ID为唯一标志的, 因此传入参数只有群号, 会长ID, 请确保公会是前2W名
    """
    origin_info = get_rank(leader_id,"fav")
    if type(origin_info) == int:
        return origin_info
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
    查询本公会排名, 需要预先绑定公会。
    只能查询已经绑定的公会信息！
    """
    # 检测有无绑定信息
    group_id = ev.group_id
    config = loadConfig()
    if str(group_id) not in config:
        msg = "未绑定公会信息, 请发送[绑定公会+会长ID]来绑定公会信息\n"
        await bot.send(ev, msg, at_sender=True)
        return
    # 获取上次更新时间,假定网站更新比游戏内延迟12分钟
    lastQuertTime = config[str(group_id)]["lastQuery"]["ts"]
    if time.time() - lastQuertTime >= 42*60:
        # 上次查询时间戳有效时间42分钟,超时会触发联网查询
        msg = '缓存数据已超时, 正在在线查询......\n'
        await bot.send(ev, msg)
        code = set_clanname(int(group_id),config[str(group_id)]["leaderId"])
        if code != 0:
            msg = f'发生错误{code}, 可能的原因：公会更换了会长/工会排名不在前2W名/传入的时间戳不正确。\n如果非上述原因, 请联系维护并提供此信息。\n'
            await bot.send(ev, msg)
            return
        else:
            config = loadConfig() # 信息已经被缓存, 重新读取
    last_query_info = config[str(group_id)]["lastQuery"]
    msg = process(last_query_info,self_clan_query_list)
    await bot.send(ev, msg)
    

@sv_push.on_prefix(['绑定公会','绑定工会'])
async def set_clan(bot,ev:CQEvent):
    """
    为一个公会绑定信息, 需要会长ID
    """
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.send(ev, '您操作得太快了, 请稍等一会儿', at_sender=True)
        return
    _lmt.start_cd(uid)
    group_id = ev.group_id
    leader_id = ev.message.extract_plain_text()
    if not leader_id.isdigit():
        await bot.send(ev, '请正确输入会长ID', at_sender=True)
        return
    code = set_clanname(int(group_id),int(leader_id))
    if code != 0:
        msg = f'发生错误{code}, 可能的原因：网络错误/ID输入错误/工会排名不在前2W名。\n如果非上述原因, 请联系维护并提供此信息。'
        await bot.send(ev, msg, at_sender=True)
        return
    msg = f"绑定成功\n"
    await bot.send(ev, msg)
    # 发送绑定过程中的查询结果
    clanrank_config = loadConfig()
    last_query_info = clanrank_config[str(group_id)]["lastQuery"]
    msg = process(last_query_info,self_clan_query_list)
    await bot.send(ev, msg, at_sender=False)  


@sv_push.scheduled_job('cron',hour='5',minute='30')
async def clanrank_push_cn():
    bot = nonebot.get_bot()
    config = loadConfig()
    for g_id in config:
        msg = ''
        origin_info = get_rank(config[g_id]["leaderId"],"fav")
        if type(origin_info) == int:
            msg += f"查询本日5时公会战信息时发生网络错误{origin_info},请联系维护"
        result = len(origin_info['data'])
        if origin_info['code'] != 0:
            # Bad request
            msg += f"查询本日5时公会战信息时发生错误{origin_info['code']}"
        elif result == 0:
            msg += "没有查询到本日5时的公会战排名信息, 可能已掉出前2W名"
        elif time.time() - origin_info['ts'] >= 45*60:
            # 获得的数据是超过45分钟以前的, 说明网站不再更新, 公会战结束
            return
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
        await bot.send(ev, '您查询得太快了, 请稍等一会儿', at_sender=True)
        return
    clan_name = ev.message.extract_plain_text()
    if inject_regex.match(clan_name):
            await bot.send(ev, "发现尝试注入行为, 您将被拉黑24小时")
            set_block_user(uid, timedelta(hours=24))
            await notify_master(f'群{ev.group_id}内的{uid}尝试向clanrank注入。')
            return
    info = get_rank(clan_name, "name")
    if type(info) == int:
        msg = f'查询出现错误{info}，请联系维护者'
    else:
        msg = process(info,leader_id_query_list)
        msg += f"查询有{_time_limit}秒冷却"
        _lmt.start_cd(uid)
    await bot.send(ev, msg)


@sv_query.on_prefix('查询会长')
async def rank_query_by_leader(bot, ev: CQEvent):
    """
    通过会长名字查询排名
    """
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.send(ev, '您查询得太快了, 请稍等一会儿', at_sender=True)
        return
    leader_name = ev.message.extract_plain_text()
    if inject_regex.match(leader_name):
            await bot.send(ev, "发现尝试注入行为, 您将被拉黑24小时")
            set_block_user(uid, timedelta(hours=24))
            await notify_master(f'群{ev.group_id}内的{uid}尝试向clanrank注入。')
            return
    info = get_rank(leader_name, "leader")
    if type(info) == int:
        msg = f'查询出现错误{info}，请联系维护者'
    else:
        msg = process(info,leader_id_query_list)
        msg += f"查询有{_time_limit}秒冷却"
        _lmt.start_cd(uid)
    await bot.send(ev, msg)


@sv_query.on_prefix('查询排名')
async def rank_query_by_rank(bot, ev: CQEvent):
    """
    查看指定名次的公会信息
    """
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.send(ev, '您查询得太快了, 请稍等一会儿', at_sender=True)
        return
    rank = ev.message.extract_plain_text()
    if not rank.isdigit():
        await bot.send(ev, '请正确输入数字', at_sender=True)
        return
    info = get_rank(rank, "rank")
    if type(info) == int:
        msg = f'查询出现错误{info}，请联系维护者'
    else:
        msg = process(info,leader_id_query_list)
        msg += f"查询有{_time_limit}秒冷却"
        _lmt.start_cd(uid)
    await bot.send(ev, msg)

@sv_query.on_fullmatch('分数线')
async def damage_line(bot, ev: CQEvent):
    """
    通过line接口来查询分数线，共14条信息
    """
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.send(ev, '您查询得太快了, 请稍等一会儿', at_sender=True)
        return
    info = get_rank("nothing", "line")
    if type(info) == int:
        msg = f'查询出现错误{info}，请联系维护者'
    else:
        msg = process(info,line_list)
        msg += f"查询有{_time_limit}秒冷却"
        _lmt.start_cd(uid)
    await bot.send(ev, msg)

