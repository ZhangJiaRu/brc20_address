from database import db  # 从 database.py 导入 db

class AddressRemark(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # 主键ID
    address = db.Column(db.String(50), unique=True, nullable=False)  # 地址，唯一键
    remark = db.Column(db.String(100), nullable=True)  # 备注，可为空

    def __repr__(self):
        return f'<AddressRemark {self.address}>'