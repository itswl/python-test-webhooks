import requests
import json
from logger import logger
from config import Config


def analyze_webhook_with_ai(webhook_data):
    """
    使用 AI 分析 webhook 数据
    
    Args:
        webhook_data: webhook 数据字典
    
    Returns:
        dict: AI 分析结果
    """
    try:
        # 提取关键信息
        source = webhook_data.get('source', 'unknown')
        parsed_data = webhook_data.get('parsed_data', {})
        
        # 构建分析提示词
        prompt = f"""
请分析以下 webhook 数据:

来源: {source}
数据内容: {json.dumps(parsed_data, ensure_ascii=False, indent=2)}

请提供以下分析:
1. 事件类型和重要性级别 (高/中/低)
2. 关键信息摘要
3. 建议的后续处理动作
4. 潜在风险或注意事项

请以JSON格式返回分析结果。
"""
        
        # 这里使用简单的规则分析,你可以替换为真实的 AI API
        analysis = analyze_with_rules(parsed_data, source)
        
        logger.info(f"AI 分析完成: {source}")
        return analysis
        
    except Exception as e:
        logger.error(f"AI 分析失败: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': f'分析失败: {str(e)}',
            'importance': 'unknown'
        }


def analyze_with_rules(data, source):
    """
    基于规则的简单分析(可替换为真实 AI)
    
    Args:
        data: 要分析的数据
        source: 数据来源
    
    Returns:
        dict: 分析结果
    """
    # 基础分析结果
    analysis = {
        'source': source,
        'event_type': data.get('event', 'unknown'),
        'importance': 'medium',
        'summary': '',
        'actions': [],
        'risks': []
    }
    
    # 根据事件类型判断重要性
    event = str(data.get('event', '')).lower()
    
    if any(keyword in event for keyword in ['error', 'failure', 'critical', 'alert']):
        analysis['importance'] = 'high'
        analysis['summary'] = f'检测到严重事件: {event}'
        analysis['actions'].append('立即查看详细日志')
        analysis['actions'].append('通知相关负责人')
        analysis['risks'].append('可能影响服务稳定性')
        
    elif any(keyword in event for keyword in ['success', 'completed', 'finished']):
        analysis['importance'] = 'low'
        analysis['summary'] = f'正常完成事件: {event}'
        analysis['actions'].append('记录到日志')
        
    elif any(keyword in event for keyword in ['user', 'order', 'payment']):
        analysis['importance'] = 'high'
        analysis['summary'] = f'业务关键事件: {event}'
        analysis['actions'].append('验证数据完整性')
        analysis['actions'].append('更新业务状态')
        
    else:
        analysis['summary'] = f'一般事件: {event}'
        analysis['actions'].append('常规处理')
    
    # 检查数据字段
    if 'user_id' in data or 'email' in data:
        analysis['data_type'] = 'user_related'
    if 'amount' in data or 'price' in data:
        analysis['data_type'] = 'financial'
        analysis['risks'].append('涉及财务数据,需要额外验证')
    
    # 生成摘要
    if not analysis['summary']:
        analysis['summary'] = f'收到来自 {source} 的 webhook 事件'
    
    return analysis


def forward_to_remote(webhook_data, analysis_result, target_url=None):
    """
    将分析后的数据转发到远程服务器
    
    Args:
        webhook_data: 原始 webhook 数据
        analysis_result: AI 分析结果
        target_url: 目标服务器地址
    
    Returns:
        dict: 转发结果
    """
    # 检查是否启用转发
    if not Config.ENABLE_FORWARD:
        logger.info("转发功能已禁用")
        return {
            'status': 'disabled',
            'message': '转发功能已禁用'
        }
    
    if target_url is None:
        target_url = Config.FORWARD_URL
    
    try:
        # 构建转发数据
        forward_data = {
            'original_data': webhook_data.get('parsed_data', {}),
            'original_source': webhook_data.get('source', 'unknown'),
            'original_timestamp': webhook_data.get('timestamp'),
            'ai_analysis': analysis_result,
            'processed_by': 'webhook-analyzer',
            'client_ip': webhook_data.get('client_ip')
        }
        
        # 发送到远程服务器
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Source': f"analyzed-{webhook_data.get('source', 'unknown')}",
            'X-Analysis-Importance': analysis_result.get('importance', 'unknown')
        }
        
        logger.info(f"转发数据到 {target_url}")
        response = requests.post(
            target_url,
            json=forward_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"成功转发到远程服务器: {target_url}")
            return {
                'status': 'success',
                'response': response.json() if response.content else {},
                'status_code': response.status_code
            }
        else:
            logger.warning(f"转发失败,状态码: {response.status_code}")
            return {
                'status': 'failed',
                'status_code': response.status_code,
                'response': response.text
            }
            
    except requests.exceptions.Timeout:
        logger.error(f"转发超时: {target_url}")
        return {
            'status': 'timeout',
            'message': '请求超时'
        }
    except requests.exceptions.ConnectionError:
        logger.error(f"无法连接到远程服务器: {target_url}")
        return {
            'status': 'connection_error',
            'message': '无法连接到远程服务器'
        }
    except Exception as e:
        logger.error(f"转发失败: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }
