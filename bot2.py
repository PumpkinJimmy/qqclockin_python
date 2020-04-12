from aiocqhttp import CQHttp, Event
import aiocqhttp
from monitor import Monitor

bot = aiocqhttp.CQHttp(api_root="http://127.0.0.1:5700")
@bot.on_message('group')
async def handle_group_msg(event: Event):
    if event.group_id in monitor_groups:
        await monitors[event.group_id].handle(event)
    else:
        bot.logger.debug(f"Message from Gid:{event.group_id} ignore")

@bot.on_notice('group_decrease')
async def handle_decrease(event: Event):
    await monitors[event.group_id].handle_decrease(event)

@bot.on_message('private')
async def handle_prv_msg(event: Event):
    if event.user_id == 996344439:
        for gid in monitor_groups:
            await monitors[gid].gen_excel()
    

monitor_groups = [
    1053085051,
    1084425828,
    1083252518,
    1084369026]

monitors = {gid:Monitor(gid,bot) for gid in monitor_groups}
bot.run(host="127.0.0.1", port=8080)



