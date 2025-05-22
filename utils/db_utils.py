# utils/db_utils.py
import os
import re
import psycopg2
from dotenv import load_dotenv

def get_db_connection():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    # 清理可能存在的引号
    if db_url and db_url.startswith(('"', "'")) and db_url.endswith(('"', "'")):
        db_url = db_url[1:-1]
    
    if not db_url:
        raise ValueError("DATABASE_URL 环境变量未设置")
    
    # 手动解析URL
    pattern = r'^(?P<scheme>[^:]+)://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>\d+)/(?P<dbname>.+)$'
    match = re.match(pattern, db_url)
    
    if not match:
        pattern_no_port = r'^(?P<scheme>[^:]+)://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:/]+)/(?P<dbname>.+)$'
        match = re.match(pattern_no_port, db_url)
        
        if not match:
            raise ValueError(f"无法解析数据库URL: {db_url}")
        
        params = match.groupdict()
        params['port'] = 5432
    else:
        params = match.groupdict()
    
    # 确保参数类型正确
    port = int(params['port'])
    host = params['host']
    user = params['user']
    password = params['password']
    dbname = params['dbname']
    
    # 连接数据库
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )