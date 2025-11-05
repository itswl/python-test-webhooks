from flask import Flask, request, jsonify
from datetime import datetime
from config import Config
from logger import logger
from utils import verify_signature, save_webhook_data, get_client_ip

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
        
        # 这里可以添加你的业务逻辑处理
        # 例如: process_webhook_data(data, source)
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'message': 'Webhook received successfully',
            'timestamp': datetime.now().isoformat(),
            'data_saved': filepath
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
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'message': f'Webhook from {source} received successfully',
            'timestamp': datetime.now().isoformat(),
            'source': source
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
