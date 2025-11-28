"""
Hardware routes for Restaurant POS System
Provides web interface for hardware testing and management
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file, current_app
from flask_login import login_required, current_user
from .test_interface import HardwareTestInterface
from .printer import PrinterManager
from .cash_drawer import CashDrawerManager
import json
import os
from datetime import datetime

bp = Blueprint('hardware', __name__, url_prefix='/hardware')


@bp.route('/')
@login_required
def dashboard():
    """Hardware dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied. Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    test_interface = HardwareTestInterface()
    hardware_status = test_interface.get_hardware_status()
    
    return render_template('hardware/dashboard.html', 
                         hardware_status=hardware_status,
                         test_interface=test_interface)


@bp.route('/test')
@login_required
def run_test():
    """Run comprehensive hardware test"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    test_interface = HardwareTestInterface()
    test_results = test_interface.run_comprehensive_test()
    
    return jsonify(test_results)


@bp.route('/test/printer/<printer_name>')
@login_required
def test_printer(printer_name):
    """Test specific printer"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    test_interface = HardwareTestInterface()
    test_result = test_interface.test_printer_only(printer_name)
    
    return jsonify(test_result)


@bp.route('/test/cash-drawer/<drawer_name>')
@login_required
def test_cash_drawer(drawer_name):
    """Test specific cash drawer"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    test_interface = HardwareTestInterface()
    test_result = test_interface.test_cash_drawer_only(drawer_name)
    
    return jsonify(test_result)


@bp.route('/print-test/<printer_name>')
@login_required
def print_test_receipt(printer_name):
    """Print test receipt"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    test_interface = HardwareTestInterface()
    result = test_interface.print_test_receipt(printer_name)
    
    return jsonify(result)


@bp.route('/open-drawer/<drawer_name>')
@login_required
def open_test_drawer(drawer_name):
    """Open test cash drawer"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    test_interface = HardwareTestInterface()
    result = test_interface.open_test_drawer(drawer_name)
    
    return jsonify(result)


@bp.route('/printers')
@login_required
def printers():
    """Printers management page"""
    if not current_user.can_access_manager_features():
        flash('Access denied. Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    printer_manager = PrinterManager()
    all_printers = printer_manager.get_all_printers()
    
    return render_template('hardware/printers.html', printers=all_printers)


@bp.route('/cash-drawers')
@login_required
def cash_drawers():
    """Cash drawers management page"""
    if not current_user.can_access_manager_features():
        flash('Access denied. Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    cash_drawer_manager = CashDrawerManager()
    all_drawers = cash_drawer_manager.get_all_drawers()
    
    return render_template('hardware/cash_drawers.html', cash_drawers=all_drawers)


@bp.route('/settings')
@login_required
def settings():
    """Hardware settings page"""
    if not current_user.can_access_manager_features():
        flash('Access denied. Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    test_interface = HardwareTestInterface()
    hardware_status = test_interface.get_hardware_status()
    
    return render_template('hardware/settings.html', 
                         hardware_status=hardware_status)


@bp.route('/settings/save', methods=['POST'])
@login_required
def save_settings():
    """Save hardware settings"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        settings = request.get_json()
        
        # Here you would save settings to database or config file
        # For now, just return success
        
        flash('Hardware settings saved successfully', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/export-results')
@login_required
def export_results():
    """Export test results"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    test_interface = HardwareTestInterface()
    test_results = test_interface.run_comprehensive_test()
    
    export_format = request.args.get('format', 'json')
    content = test_interface.export_test_results(test_results, export_format)
    
    if export_format == 'html':
        filename = f"hardware_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(current_app.instance_path, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    else:
        filename = f"hardware_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(current_app.instance_path, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return send_file(filepath, as_attachment=True, download_name=filename)


@bp.route('/history')
@login_required
def test_history():
    """Test history page"""
    if not current_user.can_access_manager_features():
        flash('Access denied. Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    test_interface = HardwareTestInterface()
    history = test_interface.get_test_history()
    
    return render_template('hardware/history.html', history=history)


@bp.route('/api/status')
@login_required
def api_status():
    """API endpoint for hardware status"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    test_interface = HardwareTestInterface()
    status = test_interface.get_hardware_status()
    
    return jsonify(status)


@bp.route('/api/refresh')
@login_required
def api_refresh():
    """API endpoint to refresh hardware detection"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    # Create new instances to refresh detection
    printer_manager = PrinterManager()
    cash_drawer_manager = CashDrawerManager()
    
    return jsonify({
        'success': True,
        'printers': printer_manager.get_all_printers(),
        'cash_drawers': cash_drawer_manager.get_all_drawers()
    })


@bp.route('/api/set-default-printer', methods=['POST'])
@login_required
def api_set_default_printer():
    """API endpoint to set default printer"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        printer_name = data.get('printer_name')
        
        if not printer_name:
            return jsonify({'error': 'Printer name required'}), 400
        
        printer_manager = PrinterManager()
        success = printer_manager.set_default_printer(printer_name)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Printer not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/api/set-default-drawer', methods=['POST'])
@login_required
def api_set_default_drawer():
    """API endpoint to set default cash drawer"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        drawer_name = data.get('drawer_name')
        
        if not drawer_name:
            return jsonify({'error': 'Drawer name required'}), 400
        
        cash_drawer_manager = CashDrawerManager()
        success = cash_drawer_manager.set_default_drawer(drawer_name)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Cash drawer not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400