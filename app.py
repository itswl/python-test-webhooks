from flask import Flask, request, jsonify, render_template
from datetime import datetime
from config import Config
from logger import logger
from utils import verify_signature, save_webhook_data, get_client_ip, get_all_webhooks
from ai_analyzer import analyze_webhook_with_ai, forward_to_remote
import os

app = Flask(__name__)
app.config.from_object(Config)


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'webhook-receiver'
    }), 200


@app.route('/', methods=['GET'])
def dashboard():
    """Webhook 数据展示页面"""
    return render_template('dashboard.html')


@app.route('/api/webhooks', methods=['GET'])
def list_webhooks():
    """获取 webhook 列表 API"""
    limit = request.args.get('limit', 50, type=int)
    webhooks = get_all_webhooks(limit=limit)
    return jsonify({
        'success': True,
        'count': len(webhooks),
        'data': webhooks
    }), 200


@app.route('/webhook', methods=['POST'])
def receive_webhook():
    """
    接收 webhook 的主要接口
    
    请求头示例:
        X-Webhook-Signature: <hmac-sha256-signature>
        X-Webhook-Source: <source-name>
    """
    try:
        # 获取请求信息
        client_ip = get_client_ip(request)
        signature = request.headers.get('X-Webhook-Signature', '')
        source = request.headers.get('X-Webhook-Source', 'unknown')
        
        # 获取原始请求体
        payload = request.get_data()
        
        # 记录接收到的 webhook
        logger.info(f"收到来自 {client_ip} 的 webhook 请求, 来源: {source}")
        logger.debug(f"原始请求体: {payload.decode('utf-8', errors='ignore')[:500]}...")  # 只记录前500个字符
        logger.debug(f"请求头: {dict(request.headers)}")
        
        # 验证签名(如果提供了签名)
        if signature:
            if not verify_signature(payload, signature):
                logger.warning(f"签名验证失败: IP={client_ip}, Source={source}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid signature'
                }), 401
            logger.info(f"签名验证成功: Source={source}")
        
        # 解析 JSON 数据
        try:
            data = request.get_json()
        except Exception as e:
            logger.error(f"JSON 解析失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Invalid JSON payload'
            }), 400
        
        # 保存 webhook 数据(包含完整的原始信息)
        filepath = save_webhook_data(
            data=data, 
            source=source,
            raw_payload=payload,
            headers=request.headers,
            client_ip=client_ip
        )
        logger.info(f"Webhook 数据已保存: {filepath}")
        
        # AI 分析 webhook 数据
        webhook_full_data = {
            'source': source,
            'parsed_data': data,
            'timestamp': datetime.now().isoformat(),
            'client_ip': client_ip
        }
        
        logger.info("开始 AI 分析...")
        analysis_result = analyze_webhook_with_ai(webhook_full_data)
        logger.info(f"AI 分析结果: {analysis_result.get('importance', 'unknown')} - {analysis_result.get('summary', '')}")
        
        # 转发到远程服务器
        forward_result = forward_to_remote(webhook_full_data, analysis_result)
        logger.info(f"转发结果: {forward_result.get('status', 'unknown')}")
        
        # 返回成功响应(包含分析和转发结果)
        return jsonify({
            'success': True,
            'message': 'Webhook received, analyzed and forwarded successfully',
            'timestamp': datetime.now().isoformat(),
            'data_saved': filepath,
            'ai_analysis': analysis_result,
            'forward_status': forward_result.get('status', 'unknown')
        }), 200
        
    except Exception as e:
        logger.error(f"处理 webhook 时发生错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/webhook/<source>', methods=['POST'])
def receive_webhook_with_source(source):
    """
    接收指定来源的 webhook
    
    Args:
        source: webhook 来源标识
    """
    try:
        # 获取请求信息
        client_ip = get_client_ip(request)
        signature = request.headers.get('X-Webhook-Signature', '')
        
        # 获取原始请求体
        payload = request.get_data()
        
        # 记录接收到的 webhook
        logger.info(f"收到来自 {client_ip} 的 webhook 请求, 来源: {source}")
        logger.debug(f"原始请求体: {payload.decode('utf-8', errors='ignore')[:500]}...")  # 只记录前500个字符
        logger.debug(f"请求头: {dict(request.headers)}")
        
        # 验证签名(如果提供了签名)
        if signature:
            if not verify_signature(payload, signature):
                logger.warning(f"签名验证失败: IP={client_ip}, Source={source}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid signature'
                }), 401
        
        # 解析 JSON 数据
        try:
            data = request.get_json()
        except Exception as e:
            logger.error(f"JSON 解析失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Invalid JSON payload'
            }), 400
        
        # 保存 webhook 数据(包含完整的原始信息)
        filepath = save_webhook_data(
            data=data, 
            source=source,
            raw_payload=payload,
            headers=request.headers,
            client_ip=client_ip
        )
        logger.info(f"Webhook 数据已保存: {filepath}")
        
        # AI 分析 webhook 数据
        webhook_full_data = {
            'source': source,
            'parsed_data': data,
            'timestamp': datetime.now().isoformat(),
            'client_ip': client_ip
        }
        
        logger.info("开始 AI 分析...")
        analysis_result = analyze_webhook_with_ai(webhook_full_data)
        logger.info(f"AI 分析结果: {analysis_result.get('importance', 'unknown')} - {analysis_result.get('summary', '')}")
        
        # 转发到远程服务器
        forward_result = forward_to_remote(webhook_full_data, analysis_result)
        logger.info(f"转发结果: {forward_result.get('status', 'unknown')}")
        
        # 返回成功响应(包含分析和转发结果)
        return jsonify({
            'success': True,
            'message': f'Webhook from {source} received, analyzed and forwarded successfully',
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'ai_analysis': analysis_result,
            'forward_status': forward_result.get('status', 'unknown')
        }), 200
        
    except Exception as e:
        logger.error(f"处理 webhook 时发生错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """405 错误处理"""
    return jsonify({
        'success': False,
        'error': 'Method not allowed'
    }), 405


if __name__ == '__main__':
    logger.info(f"启动 Webhook 服务: http://{Config.HOST}:{Config.PORT}")
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
