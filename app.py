from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import json
import time
import math

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # 数据库配置
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from database import db  # 从 database.py 导入 db
db.init_app(app)  # 初始化 db

from models import AddressRemark  # 导入模型

# API密钥和常量
UNISAT_API_KEY = "f6a92aa46c86d9c2b30094db26826b2b01876837c9f27e48bddcbfa1ea30e088"

# 辅助函数：获取铭文信息
def get_token_info(ticker):
    url = f"https://open-api.unisat.io/v1/indexer/brc20/{ticker}/info"
    headers = {
        "Authorization": f"Bearer {UNISAT_API_KEY}"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()['data']
        else:
            return None
    except Exception as e:
        print(f"获取铭文信息失败: {e}")
        return None

# 辅助函数：获取持有者列表（支持分页）
def get_holders(ticker, total_supply, start=0, limit=20):
    url = f"https://open-api.unisat.io/v1/indexer/brc20/{ticker}/holders?start={start}&limit={limit}"
    headers = {
        "Authorization": f"Bearer {UNISAT_API_KEY}"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()['data']
            all_holders = data.get('detail', [])
            total = data.get('total', 0)
            
            # 批量获取地址备注
            addresses = [holder['address'] for holder in all_holders]
            remarks = {r.address: r.remark for r in AddressRemark.query.filter(AddressRemark.address.in_(addresses)).all()}
            
            for holder in all_holders:
                amount = float(holder.get('overallBalance', 0))
                holder['percentage'] = (amount / total_supply * 100) if total_supply > 0 else 0
                holder['remark'] = remarks.get(holder['address'], holder['address'])
            
            # 计算分页信息
            total_pages = math.ceil(total / limit)
            has_prev = start > 0
            has_next = start + limit < total
            
            return {
                'holders': all_holders,
                'pagination': {
                    'start': start,
                    'limit': limit,
                    'total': total,
                    'total_pages': total_pages,
                    'has_prev': has_prev,
                    'has_next': has_next,
                    'next_start': start + limit if has_next else None
                }
            }
        else:
            print(f"Unisat API 错误: {response.status_code}, {response.text}")
            return {'holders': [], 'pagination': {}}
    except Exception as e:
        print(f"获取持有人列表失败: {e}")
        return {'holders': [], 'pagination': {}}
    
# 辅助函数：获取地址信息，使用OKX API
def get_address_info(address):
    url = "https://web3.okx.com/priapi/v2/wallet/asset/profile/all/explorer"
    t = int(time.time() * 1000)  # 生成时间戳
    url = f"{url}?t={t}"
    headers = {
        'accept': 'application/json',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        'app-type': 'web',
        'device-token': '28dd5bca-67fa-4268-82ba-8b6821c09809',
        'devid': '28dd5bca-67fa-4268-82ba-8b6821c09809',
        'origin': 'https://web3.okx.com',
        'platform': 'web',
        'priority': 'u=1, i',
        'referer': f"https://web3.okx.com/zh-hans/portfolio/{address}",
        'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'x-cdn': 'https://web3.okx.com',
        'x-fptoken': 'eyJraWQiOiIxNjgzMzgiLCJhbGciOiJFUzI1NiJ9.eyJpYXQiOjE3NDU4ODg2MjEsImVmcCI6IlZUQStTUnVvWS9pRm9rd1NBUUg1ekFnMkJUVGN5WlJ3a0Z0Z0E1QVNrUHJMaVdRdW9aUW1nUCtONlgzVUwrakgiLCJkaWQiOiIiLCJjcGsiOiJNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUVyZW80UHdNa1kvN0VrZ1JQOWJIS0lGM3VaQUQ4TTZQS3JRQ2JlajlYZjF0aGdWL0FuVWlqenhJQUt1Q2t5R2hPdCtrcGcybU9VcGc0TnR1eDFpSlJYdz09In0.7WcnaGC8lCjuaeR-aGrwZlgtZk1odo7thOPdFyjPCBij8TjGvLyL1bcbdMnHgZvkhiV35l0PVymsky1kPW8GDw',
        'x-fptoken-signature': '{P1363}5r168IWMtU4eUeHxGse1rSIxomGrGdWmqNFnp++ZahwHjzTYtB0Iu/CKFhDraiATpddyiWm9TlZqnblPqGOWjQ==',
        'x-id-group': '2130758886547070001-c-7',
        'x-locale': 'zh_CN',
        'x-request-timestamp': str(t),
        'x-simulated-trading': 'undefined',
        'x-site-info': '==QfzojI5RXa05WZiwiIMFkQPx0Rfh1SPJiOiUGZvNmIsIySIJiOi42bpdWZyJye',
        'x-utc': '8',
        'x-zkdex-env': '0',
        'content-type': 'application/json',
        'Host': 'web3.okx.com',
        'Connection': 'keep-alive'
    }
    data = {
        "userUniqueId": "7D4BD6C3-9C7B-4CB5-9E76-39C2BF72E3E0",
        "hideValueless": False,
        "address": address,
        "forceRefresh": True,
        "page": 1,
        "limit": 20,
        "chainIndexes": []
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200 and response.json()['code'] == 0:
            return response.json()
        else:
            print(f"OKX API错误: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"获取地址信息失败: {e}")
        return None

# 路由：首页
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form['query']
        if len(query) == 4:
            # 4 位字符，查询铭文
            token_info = get_token_info(query)
            if token_info:
                return redirect(url_for('token_detail', ticker=query))
        elif query.startswith('bc1p') or query.startswith('bc1q'):
            # 以 bc1p 或 bc1q 开头，查询地址
            address_info = get_address_info(query)
            if address_info:
                return redirect(url_for('address_detail', address=query))
        # 不符合条件或查询失败
        return render_template('index.html', error="请输入 4 位铭文或以 bc1p/bc1q 开头的地址")
    return render_template('index.html', error=None)

# 路由：铭文详情（支持分页）
@app.route('/token/<ticker>')
def token_detail(ticker):
    start = request.args.get('start', 0, type=int)
    limit = 20  # 每页固定 20 条记录
    
    token_info = get_token_info(ticker)
    if not token_info:
        return render_template('index.html', error=f"未找到铭文 {ticker}")
    
    holders_data = get_holders(ticker, int(token_info['max']), start, limit)
    return render_template('token_detail.html', 
                         token=token_info, 
                         holders=holders_data['holders'], 
                         pagination=holders_data['pagination'],
                         ticker=ticker)

@app.route('/token/<ticker>/holders', methods=['GET'])
def get_more_holders(ticker):
    start = request.args.get('start', 0, type=int)
    limit = 20  # 每页固定 20 条记录
    
    token_info = get_token_info(ticker)
    if not token_info:
        return jsonify({'success': False, 'message': f"未找到铭文 {ticker}"})
    
    holders_data = get_holders(ticker, int(token_info['max']), start, limit)
    return jsonify({
        'success': True,
        'holders': holders_data['holders'],
        'pagination': holders_data['pagination']
    })

# 路由：地址详情
@app.route('/address/<address>')
def address_detail(address):
    address_info = get_address_info(address)
    if not address_info:
        return render_template('index.html', error=f"未找到地址 {address} 的信息")
    remark_obj = AddressRemark.query.filter_by(address=address).first()
    remark = remark_obj.remark if remark_obj else None
    return render_template('address_detail.html', address=address, info=address_info, remark=remark)

# 路由：备注管理（支持搜索）
@app.route('/remarks', methods=['GET', 'POST'])
def remarks():
    if request.method == 'POST':
        if 'bulk_import' in request.form:
            # 批量导入备注
            bulk_data = request.form['bulk_import'].strip()
            for line in bulk_data.split('\n'):
                if ',' in line:
                    address, remark = [x.strip() for x in line.split(',', 1)]
                    if address:
                        existing = AddressRemark.query.filter_by(address=address).first()
                        if existing:
                            existing.remark = remark
                        else:
                            new_remark = AddressRemark(address=address, remark=remark)
                            db.session.add(new_remark)
            db.session.commit()
        else:
            # 单个添加/编辑备注
            address = request.form['address'].strip()
            remark = request.form['remark'].strip()
            if address:
                existing = AddressRemark.query.filter_by(address=address).first()
                if existing:
                    # 地址已存在，更新备注
                    existing.remark = remark
                    db.session.commit()
                    return redirect(url_for('remarks'))
                else:
                    # 新增地址备注
                    new_remark = AddressRemark(address=address, remark=remark)
                    db.session.add(new_remark)
                    db.session.commit()
                    return redirect(url_for('remarks'))
    
    # 处理搜索
    search_query = request.args.get('search', '').strip()
    if search_query:
        all_remarks = AddressRemark.query.filter(
            (AddressRemark.address.contains(search_query)) |
            (AddressRemark.remark.contains(search_query))
        ).all()
    else:
        all_remarks = AddressRemark.query.all()
    
    prefill_address = request.args.get('address', '')  # 支持跳转式预填
    return render_template('remarks.html', remarks=all_remarks, prefill_address=prefill_address, search_query=search_query)

# 路由：删除备注
@app.route('/delete_remark/<int:id>')
def delete_remark(id):
    remark = AddressRemark.query.get_or_404(id)
    db.session.delete(remark)
    db.session.commit()
    return redirect(url_for('remarks'))

# 新增路由：AJAX更新备注
@app.route('/update_remark', methods=['POST'])
def update_remark():
    try:
        data = request.get_json()
        address = data.get('address', '').strip()
        remark = data.get('remark', '').strip()
        
        if not address:
            return jsonify({'success': False, 'message': '地址不能为空'})
        
        existing = AddressRemark.query.filter_by(address=address).first()
        if existing:
            existing.remark = remark
        else:
            new_remark = AddressRemark(address=address, remark=remark)
            db.session.add(new_remark)
        
        db.session.commit()
        return jsonify({'success': True, 'message': '备注更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

# 新增路由：检查地址是否存在
@app.route('/check_address', methods=['POST'])
def check_address():
    try:
        data = request.get_json()
        address = data.get('address', '').strip()
        
        if not address:
            return jsonify({'exists': False, 'remark': ''})
        
        existing = AddressRemark.query.filter_by(address=address).first()
        if existing:
            return jsonify({'exists': True, 'remark': existing.remark or ''})
        return jsonify({'exists': False, 'remark': ''})
    except Exception as e:
        return jsonify({'exists': False, 'remark': '', 'error': str(e)})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # 创建数据库表
    app.run(debug=True, port=3333)

