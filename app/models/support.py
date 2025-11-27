from datetime import datetime
from app import db
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

class SupportTicketStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_CUSTOMER = "pending_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"

class SupportTicketPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class SupportTicketCategory(enum.Enum):
    GENERAL = "general"
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    PAYMENT = "payment"
    LICENSE = "license"
    INTEGRATION = "integration"

class SupportTicket(db.Model):
    """Support ticket system for customer service"""
    __tablename__ = 'support_tickets'
    
    id = Column(Integer, primary_key=True)
    ticket_number = Column(String(20), unique=True, nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(SupportTicketCategory), nullable=False)
    priority = Column(Enum(SupportTicketPriority), nullable=False, default=SupportTicketPriority.MEDIUM)
    status = Column(Enum(SupportTicketStatus), nullable=False, default=SupportTicketStatus.OPEN)
    
    # Customer information
    customer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    customer_name = Column(String(100))
    customer_email = Column(String(255))
    customer_phone = Column(String(20))
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=True)
    
    # Assignment and resolution
    assigned_to = Column(Integer, ForeignKey('users.id'), nullable=True)
    resolution = Column(Text)
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime)
    resolved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_customer_response = Column(DateTime)
    last_staff_response = Column(DateTime)
    
    # Relationships
    customer = relationship('User', foreign_keys=[customer_id], backref='customer_tickets')
    restaurant = relationship('Restaurant', foreign_keys=[restaurant_id], backref='support_tickets')
    assigned_user = relationship('User', foreign_keys=[assigned_to], backref='assigned_tickets')
    resolved_user = relationship('User', foreign_keys=[resolved_by], backref='resolved_tickets')
    responses = relationship('SupportTicketResponse', backref='ticket', cascade='all, delete-orphan')
    attachments = relationship('SupportTicketAttachment', backref='ticket', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(SupportTicket, self).__init__(**kwargs)
        if not self.ticket_number and self.ticket_number is not None:
            self.ticket_number = self.generate_ticket_number()
    
    def generate_ticket_number(self):
        """Generate unique ticket number"""
        from app.models.user import User
        prefix = "TKT"
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        
        # Get count for today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count_today = SupportTicket.query.filter(
            SupportTicket.created_at >= today_start
        ).count()
        
        return f"{prefix}{timestamp}{count_today + 1:03d}"
    
    def to_dict(self, include_customer=False, include_responses=False):
        """Convert ticket to dictionary for API responses"""
        result = {
            'id': self.id,
            'ticket_number': self.ticket_number,
            'subject': self.subject,
            'description': self.description,
            'category': self.category.value if self.category is not None else None,
            'priority': self.priority.value if self.priority is not None else None,
            'status': self.status.value if self.status is not None else None,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None,
            'last_customer_response': self.last_customer_response.isoformat() if self.last_customer_response is not None else None,
            'last_staff_response': self.last_staff_response.isoformat() if self.last_staff_response is not None else None
        }
        
        if include_customer and self.customer:
            result['customer'] = self.customer.to_dict()
        
        if include_responses:
            result['responses'] = [response.to_dict() for response in self.responses]
        
        return result
    
    def __repr__(self):
        return f'<SupportTicket {self.ticket_number}: {self.subject}>'

class SupportTicketResponse(db.Model):
    """Responses and communications for support tickets"""
    __tablename__ = 'support_ticket_responses'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('support_tickets.id'), nullable=False)
    message = Column(Text, nullable=False)
    is_internal_note = Column(Boolean, default=False)  # Internal notes not visible to customer
    
    # Sender information
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Staff member
    sender_name = Column(String(100))  # For customer responses
    sender_email = Column(String(255))  # For customer responses
    is_customer_response = Column(Boolean, default=False)
    
    # Attachments
    has_attachments = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    sender = relationship('User', foreign_keys=[sender_id], backref='support_responses')
    attachments = relationship('SupportTicketAttachment', backref='response', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'is_internal_note': self.is_internal_note,
            'sender_name': self.sender_name,
            'sender_email': self.sender_email,
            'is_customer_response': self.is_customer_response,
            'has_attachments': self.has_attachments,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
            'sender': self.sender.to_dict() if self.sender else None
        }
    
    def __repr__(self):
        return f'<SupportTicketResponse {self.id}>'

class SupportTicketAttachment(db.Model):
    """File attachments for support tickets"""
    __tablename__ = 'support_ticket_attachments'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('support_tickets.id'), nullable=True)
    response_id = Column(Integer, ForeignKey('support_ticket_responses.id'), nullable=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # Size in bytes
    mime_type = Column(String(100))
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    uploader = relationship('User', foreign_keys=[uploaded_by], backref='uploaded_attachments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None
        }
    
    def __repr__(self):
        return f'<SupportTicketAttachment {self.original_filename}>'

class KnowledgeBaseArticle(db.Model):
    """Knowledge base articles for self-service support"""
    __tablename__ = 'knowledge_base_articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)
    excerpt = Column(Text)
    category = Column(String(50))
    tags = Column(String(500))  # Comma-separated tags
    
    # Publishing
    is_published = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    
    # Author and timestamps
    author_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime)
    
    # Relationships
    author = relationship('User', foreign_keys=[author_id], backref='kb_articles')
    
    def __init__(self, **kwargs):
        super(KnowledgeBaseArticle, self).__init__(**kwargs)
        if not self.slug and self.slug is not None:
            self.slug = self.generate_slug()
    
    def generate_slug(self):
        """Generate URL-friendly slug from title"""
        import re
        slug = re.sub(r'[^\w\s-]', '', self.title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        
        # Ensure uniqueness
        original_slug = slug
        counter = 1
        while KnowledgeBaseArticle.query.filter_by(slug=slug).first():
            slug = f"{original_slug}-{counter}"
            counter += 1
        
        return slug
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'content': self.content,
            'excerpt': self.excerpt,
            'category': self.category,
            'tags': self.tags.split(',') if self.tags is not None else [],
            'is_published': self.is_published,
            'is_featured': self.is_featured,
            'view_count': self.view_count,
            'helpful_count': self.helpful_count,
            'not_helpful_count': self.not_helpful_count,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None,
            'published_at': self.published_at.isoformat() if self.published_at is not None else None,
            'author': self.author.to_dict() if self.author else None
        }
    
    def __repr__(self):
        return f'<KnowledgeBaseArticle {self.title}>'

class FAQ(db.Model):
    """Frequently Asked Questions"""
    __tablename__ = 'faqs'
    
    id = Column(Integer, primary_key=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(50))
    priority = Column(Integer, default=0)  # Higher numbers appear first
    is_published = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'category': self.category,
            'priority': self.priority,
            'is_published': self.is_published,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None
        }
    
    def __repr__(self):
        return f'<FAQ {self.question[:50]}>'