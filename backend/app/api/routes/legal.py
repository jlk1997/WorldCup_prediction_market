from fastapi import APIRouter

from fastapi.responses import HTMLResponse



router = APIRouter(prefix="/legal", tags=["legal"])



_TERMS = """

<h1>用户服务协议</h1>

<p>欢迎使用「最后一舞：世界杯2026」。本平台提供赛事数据、娱乐竞猜与球迷社区功能。</p>

<h2>虚拟球迷币规则</h2>

<ul>

<li>球迷币通过注册赠送、签到、问答、竞猜奖励、充值等方式获得。</li>

<li>球迷币用于 AI 分析、竞猜质押、助威、擂台应援等站内消费。</li>

<li>球迷币、赛季积分、虚拟勋章均为平台内虚拟物品，<strong>不可提现、不可兑换现金、不可转赠</strong>。</li>

<li>当前版本球迷币不设过期；若政策调整将提前公告。</li>

</ul>

<h2>竞猜规则</h2>

<p>竞猜仅供娱乐参考，不构成任何投资建议或博彩服务。请理性参与，未成年人请勿付费。</p>

<h2>免责声明</h2>

<p>AI 分析结果仅供参考，平台不对预测准确性作任何保证。详见 AI 使用说明。</p>

"""



_PRIVACY = """

<h1>隐私政策</h1>

<p>我们收集邮箱用于登录验证，以及您在平台内的竞猜与消费记录。</p>

<h2>AI 数据处理</h2>

<p>当您使用 AI 分析时，我们会处理您选择的对阵、赛事状态及公开新闻摘要作为模型输入；

分析结果存储于平台数据库（agent_runs）用于缓存展示，第三方大模型服务商为 MiniMax。</p>

<p>我们不会向第三方出售您的个人信息。支付信息由支付宝处理，我们不存储银行卡号。</p>

<p>如需注销账号或导出数据，请联系客服。</p>

"""



_AI = """

<h1>AI 分析使用说明</h1>

<p>AI 输出仅供娱乐参考，不构成投注或购彩建议。</p>

<h2>计费</h2>

<ul>

<li>未登录仅可读缓存，不触发 AI、不扣币。</li>

<li>登录用户每日有免费分析次数；超出后扣球迷币；缓存命中不扣币。</li>

<li>赛季通行证用户享有额外免费次数与每日领币。</li>

</ul>

"""





@router.get("/terms", response_class=HTMLResponse)

def terms_page():

    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>用户协议</title></head><body>{_TERMS}</body></html>"





@router.get("/privacy", response_class=HTMLResponse)

def privacy_page():

    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>隐私政策</title></head><body>{_PRIVACY}</body></html>"





@router.get("/ai", response_class=HTMLResponse)

def ai_usage_page():

    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>AI 使用说明</title></head><body>{_AI}</body></html>"


