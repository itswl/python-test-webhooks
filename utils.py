import hmac
import hashlib
import json
import os
from datetime import datetime
from config import Config
from logger import logger
from models import WebhookEvent, get_session


def verify_signature(payload, signature, secret=None):
    """
    验证 webhook 签名
    
    Args:
        payload: 请求体数据
        signature: 请求头中的签名
        secret: 密钥(可选,默认使用配置中的密钥)
    
    Returns:
        bool: 签名是否有效
    """
    if secret is None:
        secret = Config.WEBHOOK_SECRET
    
    # 计算期望的签名
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # 比较签名(防止时序攻击)
    return hmac.compare_digest(expected_signature, signature)


def save_webhook_data(data, source='unknown', raw_payload=None, headers=None, client_ip=None, ai_analysis=None, forward_status='pending'):
    """
    保存 webhook 数据到数据库
    
    Args:
        data: webhook 数据(解析后的)
        source: 数据来源
        raw_payload: 原始请求体(bytes)
        headers: 请求头字典
        client_ip: 客户端IP地址
        ai_analysis: AI分析结果
        forward_status: 转发状态
    
    Returns:
        int: 保存的记录 ID
    """
    session = get_session()
    try:
        # 创建 webhook 事件记录
        webhook_event = WebhookEvent(
            source=source,
            client_ip=client_ip,
            timestamp=datetime.now(),
            raw_payload=raw_payload.decode('utf-8') if raw_payload else None,
            headers=dict(headers) if headers else {},
            parsed_data=data,
            ai_analysis=ai_analysis,
            importance=ai_analysis.get('importance') if ai_analysis else None,
            forward_status=forward_status
        )
        
        session.add(webhook_event)
        session.commit()
        
        webhook_id = webhook_event.id
        logger.info(f"Webhook 数据已保存到数据库: ID={webhook_id}")
        
        # 同时保存到文件(保留兼容性)
        save_webhook_to_file(data, source, raw_payload, headers, client_ip, ai_analysis)
        
        return webhook_id
        
    except Exception as e:
        session.rollback()
        logger.error(f"保存 webhook 数据到数据库失败: {str(e)}")
        # 失败时至少保存到文件
        return save_webhook_to_file(data, source, raw_payload, headers, client_ip, ai_analysis)
    finally:
        session.close()


def save_webhook_to_file(data, source='unknown', raw_payload=None, headers=None, client_ip=None, ai_analysis=None):
    """
    保存 webhook 数据到文件(备份方式)
    
    Args:
        data: webhook 数据(解析后的)
        source: 数据来源
        raw_payload: 原始请求体(bytes)
        headers: 请求头字典
        client_ip: 客户端IP地址
        ai_analysis: AI分析结果
    
    Returns:
        str: 保存的文件路径
    """
    # 创建数据目录
    if not os.path.exists(Config.DATA_DIR):
        os.makedirs(Config.DATA_DIR)
    
    # 生成文件名(基于时间戳)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    filename = f"{source}_{timestamp}.json"
    filepath = os.path.join(Config.DATA_DIR, filename)
    
    # 准备保存的完整数据
    full_data = {
        'timestamp': datetime.now().isoformat(),
        'source': source,
        'client_ip': client_ip,
        'headers': dict(headers) if headers else {},
        'raw_payload': raw_payload.decode('utf-8') if raw_payload else None,
        'parsed_data': data
    }
    
    # 添加 AI 分析结果
    if ai_analysis:
        full_data['ai_analysis'] = ai_analysis
    
    # 保存数据
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False)
    
    return filepath


def get_client_ip(request):
    """
    获取客户端 IP 地址
    
    Args:
        request: Flask request 对象
    
    Returns:
        str: 客户端 IP 地址
    """
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr


def get_all_webhooks(limit=50):
    """
    从数据库获取所有保存的 webhook 数据
    
    Args:
        limit: 返回的最大数量
    
    Returns:
        list: webhook 数据列表（按时间倒序）
    """
    session = get_session()
    try:
        # 从数据库查询
        events = session.query(WebhookEvent)\
            .order_by(WebhookEvent.timestamp.desc())\
            .limit(limit)\
            .all()
        
        # 转换为字典列表
        webhooks = [event.to_dict() for event in events]
        return webhooks
        
    except Exception as e:
        logger.error(f"从数据库查询 webhook 数据失败: {str(e)}")
        # 失败时降级为文件查询
        return get_webhooks_from_files(limit)
    finally:
        session.close()


def get_webhooks_from_files(limit=50):
    """
    从文件获取 webhook 数据(备份方式)
    
    Args:
        limit: 返回的最大数量
    
    Returns:
        list: webhook 数据列表（按时间倒序）
    """
    if not os.path.exists(Config.DATA_DIR):
        return []
    
    webhooks = []
    files = [f for f in os.listdir(Config.DATA_DIR) if f.endswith('.json')]
    
    # 读取所有文件
    for filename in files:
        filepath = os.path.join(Config.DATA_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['filename'] = filename
                webhooks.append(data)
        except Exception as e:
            logger.error(f"读取文件失败 {filename}: {str(e)}")
    
    # 按 timestamp 字段倒序排序（最新的在前面）
    webhooks.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # 返回限制数量的结果
    return webhooks[:limit]
