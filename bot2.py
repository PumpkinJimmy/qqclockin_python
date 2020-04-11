import os, logging
from aiocqhttp import CQHttp, Event
import aiocqhttp
import shelve
import datetime

def parse_name(s):
    s = s.strip()
    cs = s.encode()
    p = 0
    num = 0
    ep = 0
    np = 0
    while p < len(cs) and cs[p] > 127:
        p += 1
    ep = p
    if p >= len(cs) or p == 0:
        return (s,-1)
    else:
        while p < len(cs) and cs[p] in (ord(','), ord('-'), ord(' '), ord('_')):
            p += 1
        np = p
        while p < len(cs) and cs[p] >= ord('0') and cs[p] <= ord('9'):
            num = num * 10 + cs[p] - ord('0')
            p += 1
        if p < len(cs) or np == p:
            return (s,-1)
        else:
            return (cs[0:ep].decode(), num)

def parse_name2(s):
    s = s.strip()
    cs = s.encode()
    p = 0
    num = 0
    ep = 0
    np = 0
    while p < len(cs) and cs[p] >= ord('0') and cs[p] <= ord('9'): 
        num = num * 10 + cs[p] - ord('0')
        p += 1
    if p >= len(cs) or p == 0:
        return (s, -1)
    else:
        while p < len(cs) and cs[p] in (ord(','), ord('-'), ord(' '), ord('_')):
            p += 1
        ep = p
        while p < len(cs) and cs[p] > 127:
            p += 1
        if p < len(cs) or ep == p:
            return (s, -1)
        else:
            return (cs[ep:].decode(), num)

def parse_info(d):
    info = {}
    if d['card']:
        raw = d['card']
    else:
        raw = d['nickname']
    name1, id1 = parse_name(raw)
    name2, id2 = parse_name2(raw)
    uid = int(d['user_id'])
    if id1 == -1 and id2 == -1:
        info[uid] = raw
    else:
        if id1 == -1:
            info[uid] = {"name":name2, "id": id2}
        else:
            info[uid] = {"name":name1, "id": id1}
    return info

def parse_infos(data):
    info = {}
    for d in data:
        if d['card']:
            raw = d['card']
        else:
            raw = d['nickname']
        name1, id1 = parse_name(raw)
        name2, id2 = parse_name2(raw)
        uid = int(d['user_id'])
        if id1 == -1 and id2 == -1:
            info[uid] = raw
        else:
            if id1 == -1:
                info[uid] = {"name":name2, "id": id2}
            else:
                info[uid] = {"name":name1, "id": id1}
    return info

def subdir(gid, *args):
    return os.path.join(str(gid), *args)

def initLogger(groups):
    if not os.path.isfile("qqbot.log"):
        with open('qqbot.log', 'w') as f: pass
    for gid in groups:
        fh = logging.FileHandler("qqbot.log", 'a', encoding='utf8')
        fh.setLevel(logging.DEBUG)
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        logger = logging.getLogger(f"QQBotLogger_{gid}")
        logger.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(f"%(asctime)s - %(filename)s[line:%(lineno)d][Gid:{gid}] %(levelname)s: %(message)s"))
        sh.setFormatter(logging.Formatter(f"%(asctime)s - [Gid:{gid}] %(levelname)s: %(message)s"))
        logger.addHandler(fh)
        logger.addHandler(sh)

def initSubdir(groups):
    for gid in groups:
        if not os.path.isdir(str(gid)):
            os.mkdir(str(gid))

def initUserInfo(groups):
    global user_info_db
    user_info_db = {}
    for gid in groups:
        user_info_db[gid] = shelve.open(subdir(gid, 'user_info_db'))

def today_str():
    return datetime.datetime.now().strftime("%m-%d")

def initClocin(groups):
    global clockin_db
    clockin_db = {}
    for gid in groups:
        clockin_db[gid] = shelve.open(subdir(gid, today_str()))

def getLogger(gid):
    return logging.getLogger(f"QQBotLogger_{gid}")

def update_member(gid, uid, info):
    user_info_db[gid][str(uid)] = info

bot = aiocqhttp.CQHttp(api_root="http://127.0.0.1:5700")
@bot.on_message('group')
async def handle_group_msg(event: Event):
    if event.group_id in monitor_groups:
        logger = getLogger(event.group_id)
        logger.debug(f"Message Gid:{event.group_id} receive")
        if event.anonymous:
            logger.debug("Anonymous message ignore")
            return
        logger.debug(f"处理来自{event.user_id}的消息,昵称：{event.sender['nickname']}, 群名片：{event.sender['card']}")
        msg = aiocqhttp.Message(event.message)
        for seg in msg:
            uid = event.user_id
            gid = event.group_id
            raw_info = await bot.get_group_member_info(group_id=gid, user_id=uid)
            info = parse_info(raw_info)
            logger.debug(f"成员信息:{info}")
            update_member(gid, uid, info)
            logger.debug(f"成员信息已更新：{user_info_db[event.group_id][str(event.user_id)]}")
            if seg.type == "image":
                if not seg.data['file'].endswith('.gif'):
                    logger.info(f"{event.user_id} 图片打卡")
                    db = clockin_db[gid]
                    if str(uid) in db:
                        db[str(uid)] += 1
                    else:
                        db[str(uid)] = 1
                    logger.debug(f"Clockin DB: {uid}:{db[str(uid)]}")
                # res = await bot.get_image(file=seg.data['file'])
                # print("路径: ", res)
            elif seg.type == "rich":
                logger.info(f"{event.user_id} rich打卡")
    else:
        bot.logger.debug(f"Message from Gid:{event.group_id} ignore")



monitor_groups = [
    512980639,
    1053085051,
    1084425828,
    1083252518,
    1084369026]
initLogger(monitor_groups)
initSubdir(monitor_groups)
initUserInfo(monitor_groups)
initClocin(monitor_groups)
bot.run(host="127.0.0.1", port=8080)