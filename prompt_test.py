import asyncio
import logging
from dotenv import load_dotenv

from app.data.demo import test_image
from app.prompts.travel import intent_group, plan_prompt, hotel_prompt
from app.services.llm_service import LLMService
load_dotenv()
logging.basicConfig(level=logging.DEBUG)

chats = [
    {
        'user': '天柱',
        'content': '我们十一去东京周边玩5天4晚，想看富士山，顺便体验温泉酒店和米其林餐厅，大家有什么想法？'
    },
    {
        'user': '天赐',
        'content': '我们家肯定要带孩子一起、不能走太远、不然太累了'
    },
    {
        'user': '天柱',
        'content': '嗯，我老婆说体验温泉酒店，主要之前是小红书看箱根跟河口湖的酒店都不错，这个很值得打卡，孩子也轻松'
    },
    {
        'user': '天赐',
        'content': '好呀、十一安排下，走起'
    },
    {
        'user': '天柱',
        'content': '@GoodGuideAI_Bot 帮我们根据上面说的需求，出一个初步的行程方案路线，人均预算25000-30000元就可以。'
                   '主要大家都想体验富士山旁边的温泉酒店和东京的米其林餐厅。'
    },
]

chats_qa = [
    {
        'user': '天柱',
        'content': '@天赐 @丹静 你们看看上面行程有没有问题，咱们商量下啊'
    },
    {
        'user': '天赐',
        'content': '好 我也让我老婆看'
    },
    {
        'user': '天柱',
        'content': '@GoodGuideAl_Bot 帮我们看下10月1号 东方航空公司上海出发10月5号晚上回上海的往返航班、给我看一下航班信息和价格。'
    },
]
chats_qa2 = [
    {
        'user': '天赐',
        'content': '我们富士山酒店住哪呢?'
    },
    {
        'user': '天柱',
        'content': '@GoodGuideAL_Bot 有哪些富士山的温泉酒店适合我们家庭？帮忙推荐下吧'
    }
]

chats_qa3 = [
    {
        'user': '天柱',
        'content': [
            {
                "type": "text",
                "text": "@GoodGuideAL_Bot 这个地方看起来很不错，是在哪里啊？离我们箱根住的酒店远不远？"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": test_image,
                    "detail": "high"
                }
            }
        ]
    }
]


async def test():
    llm_service = LLMService()
    system_prompt = plan_prompt

    # create history
    logger = logging.getLogger(__name__)

    messages = [{"role": "system", "content": system_prompt}]

    for chat in chats:
        openai_message = {
            "role": 'user',
            "content": chat['content'],
            "name": chat['user']
        }
        messages.append(openai_message)

    for chat in chats_qa:
        openai_message = {
            "role": 'user',
            "content": chat['content'],
            "name": chat['user']
        }
        messages.append(openai_message)

    for chat in chats_qa2:
        openai_message = {
            "role": 'user',
            "content": chat['content'],
            "name": chat['user']
        }
        messages.append(openai_message)

    for chat in chats_qa3:
        openai_message = {
            "role": 'user',
            "content": chat['content'],
            "name": chat['user']
        }
        messages.append(openai_message)

    ret = await llm_service.debug(messages=messages)

    logger.info(f"ret = {ret}")

result = asyncio.run(test())
