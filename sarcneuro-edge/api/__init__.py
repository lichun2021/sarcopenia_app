"""
SarcNeuro Edge API 包
"""
# API版本
API_VERSION = "v1.0"

# API前缀
API_PREFIX = "/api"

# 常用响应格式
def success_response(data=None, message="操作成功"):
    """成功响应格式"""
    return {
        "status": "success",
        "message": message,
        "data": data,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }

def error_response(message="操作失败", error_code=None):
    """错误响应格式"""
    return {
        "status": "error", 
        "message": message,
        "error_code": error_code,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }

def paginated_response(data, total, page=1, size=10):
    """分页响应格式"""
    return {
        "status": "success",
        "data": data,
        "pagination": {
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        },
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }

__all__ = [
    "API_VERSION",
    "API_PREFIX", 
    "success_response",
    "error_response",
    "paginated_response"
]