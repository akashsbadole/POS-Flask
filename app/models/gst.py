from datetime import datetime
from app import db

class GSTSetting(db.Model):
    __tablename__ = 'gst_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    cgst_rate = db.Column(db.Numeric(5, 4), default=0.09)  # 9%
    sgst_rate = db.Column(db.Numeric(5, 4), default=0.09)  # 9%
    igst_rate = db.Column(db.Numeric(5, 4), default=0.00)  # For inter-state
    cess_rate = db.Column(db.Numeric(5, 4), default=0.00)  # Additional tax
    is_active = db.Column(db.Boolean, default=True)
    effective_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = db.relationship('Restaurant', backref='gst_settings')
    
    def get_total_gst_rate(self):
        """Get total GST rate"""
        return float(self.cgst_rate) + float(self.sgst_rate) + float(self.igst_rate) + float(self.cess_rate)
    
    def calculate_gst_components(self, amount):
        """Calculate GST components for given amount"""
        cgst_amount = float(amount) * float(self.cgst_rate)
        sgst_amount = float(amount) * float(self.sgst_rate)
        igst_amount = float(amount) * float(self.igst_rate)
        cess_amount = float(amount) * float(self.cess_rate)
        
        return {
            'cgst': cgst_amount,
            'sgst': sgst_amount,
            'igst': igst_amount,
            'cess': cess_amount,
            'total_gst': cgst_amount + sgst_amount + igst_amount + cess_amount
        }
    
    def to_dict(self):
        """Convert GST setting to dictionary for API responses"""
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'cgst_rate': float(self.cgst_rate),
            'sgst_rate': float(self.sgst_rate),
            'igst_rate': float(self.igst_rate),
            'cess_rate': float(self.cess_rate),
            'total_gst_rate': self.get_total_gst_rate(),
            'is_active': self.is_active,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<GSTSetting {self.cgst_rate}% CGST, {self.sgst_rate}% SGST>'

class HSNCode(db.Model):
    __tablename__ = 'hsn_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 4), nullable=False)  # GST rate
    category = db.Column(db.String(100))  # Goods/Services category
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    menu_items = db.relationship('MenuItem', backref='hsn_code')
    
    def to_dict(self):
        """Convert HSN code to dictionary for API responses"""
        return {
            'id': self.id,
            'code': self.code,
            'description': self.description,
            'tax_rate': float(self.tax_rate),
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<HSNCode {self.code} ({self.description})>'