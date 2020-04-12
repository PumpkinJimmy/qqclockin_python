import logging
import shelve
import datetime
import os
import glob
import aiocqhttp
from aiocqhttp import Event
import openpyxl

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
    if d['card']:
        raw = d['card']
    else:
        raw = d['nickname']
    name1, id1 = parse_name(raw)
    name2, id2 = parse_name2(raw)
    if id1 == -1 and id2 == -1:
        res = raw
    else:
        if id1 == -1:
            res = {"name":name2, "id": id2}
        else:
            res = {"name":name1, "id": id1}
    return res

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

def today_str():
    return datetime.datetime.now().strftime("%m-%d")

class Monitor:
    def __init__(self, gid, bot):
        self.gid = gid
        self.bot = bot
        if not os.path.isdir(str(gid)):
            os.mkdir(str(gid))
        self.initLogger()
        self.today = datetime.datetime.now().date()
        self.update()
        self.user_info_db = shelve.open(self.subdir('user_info_db'))
        self.clockin_db = shelve.open(self.subdir(today_str()))
        self.logger.info(f"启动监视，监视群：{self.gid}, 当前日期：{self.today}")
    
    def subdir(self, *args):
        return os.path.join(str(self.gid), *args)
    
    def initLogger(self):
        if not os.path.isfile('qqbot.log'):
            with open('qqbot.log', 'w') as f: pass
        fh = logging.FileHandler("qqbot.log", 'a', encoding='utf8')
        fh.setLevel(logging.DEBUG)
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        self.logger = logging.getLogger(f"QQBotLogger_{self.gid}")
        self.logger.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(f"%(asctime)s - %(filename)s[line:%(lineno)d][Gid:{self.gid}] %(levelname)s: %(message)s"))
        sh.setFormatter(logging.Formatter(f"%(asctime)s - [Gid:{self.gid}] %(levelname)s: %(message)s"))
        self.logger.addHandler(fh)
        self.logger.addHandler(sh)

    async def update(self):
        today = datetime.datetime.now().date()
        if today != self.today:
            await self.gen_excel()
            self.logger.info(f"已更新报表")
            self.today = today
            self.logger.info(f"日期更新至:{self.today}")
            self.clockin_db = shelve.open(self.subdir(today_str()))

    async def gen_excel(self):
        gname = (await self.bot.get_group_info(group_id=self.gid))['group_name']
        header = ["日期/ID"]
        mp = {}
        for i,(uid, info) in enumerate(self.user_info_db.items()):
            if type(info) == dict:
                info = info['name']
            header.append(info)
            mp[uid] = i + 1

        wb = openpyxl.Workbook()
        tb = wb.create_sheet(index=0, title="打卡统计")
        tb.append(header)

        fs = glob.glob(self.subdir(r'[0-9][0-9]-[0-9][0-9].dat'))
        for fn in fs:
            dbn = fn[:-4]
            clockin_db = shelve.open(dbn)
            dbn = dbn[-5:]
            self.logger.debug(f"处理数据 {dbn}")
            row = [dbn]
            row.extend([0] * len(self.user_info_db))
            for k, v in clockin_db.items():
                row[mp[k]] = v
            tb.append(row)
        wb.save(f"{gname}.xlsx")
        self.logger.info(f"报表生成，文件名：{gname}.xlsx")
        await self.bot.send_private_msg(user_id=996344439, message=f"报表已生成，文件名：{gname}.xlsx")


    async def handle(self, event:Event):
        logger = self.logger
        logger.debug(f"Message Gid:{event.group_id} receive")
        if event.anonymous:
            logger.debug("Anonymous message ignore")
            return
        logger.debug(f"处理来自{event.user_id}的消息,昵称：{event.sender['nickname']}, 群名片：{event.sender['card']}")
        msg = aiocqhttp.Message(event.message)
        for seg in msg:
            uid = event.user_id
            gid = event.group_id
            raw_info = await self.bot.get_group_member_info(group_id=gid, user_id=uid)
            info = parse_info(raw_info)
            logger.debug(f"成员信息:{info}")
            self.user_info_db[str(uid)] = info
            logger.debug(f"成员信息已更新：{self.user_info_db[str(uid)]}")
            if seg.type == "image":
                if not seg.data['file'].endswith('.gif'):
                    await self.update()
                    logger.info(f"{event.user_id} 图片打卡")
                    db = self.clockin_db
                    if str(uid) in db:
                        db[str(uid)] += 1
                    else:
                        db[str(uid)] = 1
                    logger.debug(f"Clockin DB: {uid}:{db[str(uid)]}")
            elif seg.type == "rich":
                logger.info(f"{event.user_id} rich打卡")
    
    async def handle_group_decrease(self, event:Event):
        name = (await self.bot.get_group_info(group_id=event.group_id))['group_name']
        self.logger.info(f"{event.user_id} 退出 {name}")
        if str(event.user_id) in self.user_info_db:
            del self.user_info_db[str(event.user_id)]
            self.logger.info("成员信息已更新")