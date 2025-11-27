from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.support import bp
from app.models.support import SupportTicket, SupportTicketResponse, KnowledgeBaseArticle, FAQ
from app.models.user import User
from app import db
from datetime import datetime
import json
import os

@bp.route('/')
def support_home():
    """Support home page with knowledge base and FAQ"""
    featured_articles = KnowledgeBaseArticle.query.filter_by(is_published=True, is_featured=True).limit(5).all()
    recent_articles = KnowledgeBaseArticle.query.filter_by(is_published=True).order_by(KnowledgeBaseArticle.published_at.desc()).limit(10).all()
    faqs = FAQ.query.filter_by(is_published=True).order_by(FAQ.priority.desc()).limit(10).all()
    
    return render_template('support/home.html', 
                         featured_articles=featured_articles,
                         recent_articles=recent_articles,
                         faqs=faqs)

@bp.route('/tickets')
@login_required
def tickets():
    """Support tickets list for staff"""
    if not current_user.can_access_admin_features():
        return render_template('errors/403.html'), 403
    
    return render_template('support/tickets.html')

@bp.route('/api/tickets')
@login_required
def api_tickets():
    """API endpoint for support tickets"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    category_filter = request.args.get('category', '')
    
    query = SupportTicket.query
    
    # Apply filters
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    if category_filter:
        query = query.filter_by(category=category_filter)
    
    # Order by most recent
    tickets = query.order_by(SupportTicket.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'tickets': [ticket.to_dict(include_customer=True) for ticket in tickets.items],
        'pagination': {
            'page': tickets.page,
            'pages': tickets.pages,
            'per_page': tickets.per_page,
            'total': tickets.total,
            'has_next': tickets.has_next,
            'has_prev': tickets.has_prev
        }
    })

@bp.route('/tickets/new', methods=['GET', 'POST'])
def new_ticket():
    """Create new support ticket"""
    if request.method == 'GET':
        return render_template('support/new_ticket.html')
    
    data = request.get_json()
    
    try:
        ticket = SupportTicket(
            subject=data.get('subject', ''),
            description=data.get('description', ''),
            category=data.get('category', 'general'),
            priority=data.get('priority', 'medium'),
            customer_name=data.get('customer_name', ''),
            customer_email=data.get('customer_email', ''),
            customer_phone=data.get('customer_phone', ''),
            customer_id=current_user.id if current_user.is_authenticated else None
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        # Send email notification to support team
        send_support_email_notification(ticket)
        
        return jsonify({
            'success': True,
            'message': 'Support ticket created successfully',
            'ticket_number': ticket.ticket_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/tickets/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    """View support ticket details"""
    if not current_user.can_access_admin_features():
        return render_template('errors/403.html'), 403
    
    ticket = SupportTicket.query.get_or_404(ticket_id)
    return render_template('support/ticket_detail.html', ticket=ticket)

@bp.route('/tickets/<int:ticket_id>/respond', methods=['POST'])
@login_required
def respond_ticket(ticket_id):
    """Add response to support ticket"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    ticket = SupportTicket.query.get_or_404(ticket_id)
    data = request.get_json()
    
    try:
        response = SupportTicketResponse(
            ticket_id=ticket.id,
            message=data.get('message', ''),
            is_internal_note=data.get('is_internal_note', False),
            sender_id=current_user.id
        )
        
        db.session.add(response)
        
        # Update ticket status and timestamps
        ticket.status = data.get('status', ticket.status)
        ticket.last_staff_response = datetime.utcnow()
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send email notification to customer if not internal note
        if not getattr(response, 'is_internal_note', False) and getattr(ticket, 'customer_email', None) is not None:
            send_customer_response_email(ticket, response)
        
        return jsonify({
            'success': True,
            'message': 'Response added successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/tickets/<int:ticket_id>/assign', methods=['POST'])
@login_required
def assign_ticket(ticket_id):
    """Assign ticket to staff member"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    ticket = SupportTicket.query.get_or_404(ticket_id)
    data = request.get_json()
    
    try:
        ticket.assigned_to = data.get('assigned_to')
        ticket.status = 'in_progress'
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ticket assigned successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/tickets/<int:ticket_id>/resolve', methods=['POST'])
@login_required
def resolve_ticket(ticket_id):
    """Resolve support ticket"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    ticket = SupportTicket.query.get_or_404(ticket_id)
    data = request.get_json()
    
    try:
        ticket.status = 'resolved'
        ticket.resolution = data.get('resolution', '')
        ticket.resolution_notes = data.get('resolution_notes', '')
        ticket.resolved_at = datetime.utcnow()
        ticket.resolved_by = current_user.id
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send resolution email to customer
        if ticket.customer_email:
            send_resolution_email(ticket)
        
        return jsonify({
            'success': True,
            'message': 'Ticket resolved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/knowledge-base')
def knowledge_base():
    """Knowledge base home page"""
    categories = db.session.query(KnowledgeBaseArticle.category).filter_by(is_published=True).distinct().all()
    featured_articles = KnowledgeBaseArticle.query.filter_by(is_published=True, is_featured=True).all()
    
    return render_template('support/knowledge_base.html', 
                         categories=[cat[0] for cat in categories if cat[0]],
                         featured_articles=featured_articles)

@bp.route('/knowledge-base/<slug>')
def knowledge_article(slug):
    """View knowledge base article"""
    article = KnowledgeBaseArticle.query.filter_by(slug=slug, is_published=True).first_or_404()
    
    # Increment view count
    article.view_count += 1
    db.session.commit()
    
    return render_template('support/article.html', article=article)

@bp.route('/api/knowledge-base/search')
def api_search_articles():
    """Search knowledge base articles"""
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    
    articles_query = KnowledgeBaseArticle.query.filter_by(is_published=True)
    
    if query:
        articles_query = articles_query.filter(
            KnowledgeBaseArticle.title.contains(query) |
            KnowledgeBaseArticle.content.contains(query) |
            KnowledgeBaseArticle.tags.contains(query)
        )
    
    if category:
        articles_query = articles_query.filter_by(category=category)
    
    articles = articles_query.order_by(KnowledgeBaseArticle.view_count.desc()).limit(20).all()
    
    return jsonify({
        'articles': [article.to_dict() for article in articles]
    })

@bp.route('/api/knowledge-base/<int:article_id>/helpful', methods=['POST'])
def api_article_helpful(article_id):
    """Mark article as helpful or not helpful"""
    article = KnowledgeBaseArticle.query.get_or_404(article_id)
    data = request.get_json()
    
    if data.get('helpful'):
        article.helpful_count += 1
    else:
        article.not_helpful_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'helpful_count': article.helpful_count,
        'not_helpful_count': article.not_helpful_count
    })

@bp.route('/faq')
def faq():
    """FAQ page"""
    categories = db.session.query(FAQ.category).filter_by(is_published=True).distinct().all()
    faqs = FAQ.query.filter_by(is_published=True).order_by(FAQ.priority.desc()).all()
    
    return render_template('support/faq.html', 
                         categories=[cat[0] for cat in categories if cat[0]],
                         faqs=faqs)

@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact us page"""
    if request.method == 'GET':
        return render_template('support/contact.html')
    
    data = request.get_json()
    
    try:
        # Create support ticket from contact form
        ticket = SupportTicket(
            subject=data.get('subject', 'Contact Form Submission'),
            description=data.get('message', ''),
            category=data.get('category', 'general'),
            customer_name=data.get('name', ''),
            customer_email=data.get('email', ''),
            customer_phone=data.get('phone', ''),
            customer_id=current_user.id if current_user.is_authenticated else None
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        # Send email notification
        send_contact_email(ticket)
        
        return jsonify({
            'success': True,
            'message': 'Your message has been sent successfully',
            'ticket_number': ticket.ticket_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Helper functions for email notifications
def send_support_email_notification(ticket):
    """Send email notification to support team about new ticket"""
    # Implementation would depend on your email service
    # This is a placeholder for email functionality
    current_app.logger.info(f"New support ticket created: {ticket.ticket_number}")

def send_customer_response_email(ticket, response):
    """Send email notification to customer about new response"""
    # Implementation would depend on your email service
    current_app.logger.info(f"Response sent to customer for ticket: {ticket.ticket_number}")

def send_resolution_email(ticket):
    """Send email notification to customer about ticket resolution"""
    # Implementation would depend on your email service
    current_app.logger.info(f"Ticket resolved: {ticket.ticket_number}")

def send_contact_email(ticket):
    """Send email notification about contact form submission"""
    # Implementation would depend on your email service
    current_app.logger.info(f"Contact form submission: {ticket.ticket_number}")