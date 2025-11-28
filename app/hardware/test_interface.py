"""
Hardware test interface for Restaurant POS System
Provides comprehensive testing capabilities for all hardware components
"""

import json
import os
import platform
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import current_app
from .printer import PrinterManager
from .cash_drawer import CashDrawerManager


class HardwareTestInterface:
    """Comprehensive hardware testing interface"""
    
    def __init__(self):
        self.printer_manager = PrinterManager()
        self.cash_drawer_manager = CashDrawerManager()
        self.test_history = []
        self.system_info = self._get_system_info()
    
    def _get_system_info(self) -> Dict:
        """Get system information for hardware compatibility"""
        return {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'hostname': platform.node()
        }
    
    def run_comprehensive_test(self) -> Dict:
        """Run comprehensive hardware test"""
        test_results = {
            'test_time': datetime.now().isoformat(),
            'system_info': self.system_info,
            'printer_tests': self._test_all_printers(),
            'cash_drawer_tests': self._test_all_cash_drawers(),
            'summary': {}
        }
        
        # Calculate summary
        total_printers = len(test_results['printer_tests'])
        working_printers = sum(1 for test in test_results['printer_tests'] 
                              if test.get('overall_success', False))
        
        total_drawers = len(test_results['cash_drawer_tests'])
        working_drawers = sum(1 for test in test_results['cash_drawer_tests'] 
                             if test.get('overall_success', False))
        
        test_results['summary'] = {
            'total_printers': total_printers,
            'working_printers': working_printers,
            'total_drawers': total_drawers,
            'working_drawers': working_drawers,
            'overall_status': 'Success' if (working_printers > 0 and working_drawers > 0) else 'Partial',
            'recommendations': self._generate_recommendations(test_results)
        }
        
        # Save to test history
        self.test_history.append(test_results)
        
        return test_results
    
    def _test_all_printers(self) -> List[Dict]:
        """Test all available printers"""
        printer_tests = []
        
        all_printers = self.printer_manager.get_all_printers()
        
        for printer in all_printers:
            test_result = self.printer_manager.test_printer(printer)
            test_result['printer_info'] = printer
            test_result['overall_success'] = (
                test_result.get('tests', {}).get('connection', {}).get('success', False) and
                test_result.get('tests', {}).get('print', {}).get('success', False)
            )
            printer_tests.append(test_result)
        
        return printer_tests
    
    def _test_all_cash_drawers(self) -> List[Dict]:
        """Test all available cash drawers"""
        drawer_tests = []
        
        all_drawers = self.cash_drawer_manager.get_all_drawers()
        
        for drawer in all_drawers:
            test_result = self.cash_drawer_manager.test_cash_drawer(drawer)
            test_result['drawer_info'] = drawer
            test_result['overall_success'] = (
                test_result.get('tests', {}).get('connection', {}).get('success', False) and
                test_result.get('tests', {}).get('open', {}).get('success', False)
            )
            drawer_tests.append(test_result)
        
        return drawer_tests
    
    def _generate_recommendations(self, test_results: Dict) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Printer recommendations
        printer_tests = test_results.get('printer_tests', [])
        working_printers = [test for test in printer_tests if test.get('overall_success', False)]
        
        if not working_printers:
            recommendations.append("No working printers detected. Consider installing a compatible ESC/POS thermal printer.")
        elif len(working_printers) == 1:
            recommendations.append("Only one working printer detected. Consider adding a backup printer for reliability.")
        
        # Cash drawer recommendations
        drawer_tests = test_results.get('cash_drawer_tests', [])
        working_drawers = [test for test in drawer_tests if test.get('overall_success', False)]
        
        if not working_drawers:
            recommendations.append("No working cash drawers detected. Consider installing a compatible cash drawer.")
        
        # System-specific recommendations
        system = self.system_info.get('platform', '').lower()
        if system == 'windows':
            recommendations.append("For Windows: Ensure printer drivers are properly installed and USB devices are recognized.")
        elif system == 'linux':
            recommendations.append("For Linux: Ensure CUPS is properly configured and USB permissions are set.")
        elif system == 'darwin':
            recommendations.append("For macOS: Ensure printers are added to System Preferences and USB devices are recognized.")
        
        return recommendations
    
    def test_printer_only(self, printer_name: str) -> Dict:
        """Test a specific printer"""
        printer_info = self.printer_manager.get_printer_status(printer_name)
        if 'error' in printer_info:
            return {'error': 'Printer not found'}
        
        test_result = self.printer_manager.test_printer(printer_info)
        test_result['printer_info'] = printer_info
        test_result['overall_success'] = (
            test_result.get('tests', {}).get('connection', {}).get('success', False) and
            test_result.get('tests', {}).get('print', {}).get('success', False)
        )
        
        return test_result
    
    def test_cash_drawer_only(self, drawer_name: str) -> Dict:
        """Test a specific cash drawer"""
        drawer_info = self.cash_drawer_manager.get_drawer_status(drawer_name)
        if 'error' in drawer_info:
            return {'error': 'Cash drawer not found'}
        
        test_result = self.cash_drawer_manager.test_cash_drawer(drawer_info)
        test_result['drawer_info'] = drawer_info
        test_result['overall_success'] = (
            test_result.get('tests', {}).get('connection', {}).get('success', False) and
            test_result.get('tests', {}).get('open', {}).get('success', False)
        )
        
        return test_result
    
    def print_test_receipt(self, printer_name: str) -> Dict:
        """Print a test receipt on specific printer"""
        try:
            printer_info = self.printer_manager.get_printer_status(printer_name)
            if 'error' in printer_info:
                return {'success': False, 'message': 'Printer not found'}
            
            # Create test order
            test_order = self.printer_manager.create_test_receipt()
            
            # Print receipt
            if printer_info.get('type') == 'USB ESC/POS Printer':
                from escpos.printer import Usb
                printer = Usb(printer_info.get('vendor_id'), printer_info.get('product_id'))
                
                printer._raw(b'\x1b\x61\x01')  # Center align
                printer._raw(b'\x1b\x21\x08')  # Double height
                printer.text('TEST RECEIPT\n')
                printer._raw(b'\x1b\x21\x00')  # Normal text
                printer.text('=' * 32 + '\n')
                printer.text(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                printer.text(f'Printer: {printer_name}\n')
                printer.text('=' * 32 + '\n')
                printer.text('Test completed successfully!\n')
                printer.cut()
                
                return {'success': True, 'message': 'Test receipt printed successfully'}
            else:
                # Use browser printing fallback
                from app.receipt_printer import ReceiptPrinter
                printer = ReceiptPrinter()
                temp_file = printer._generate_browser_receipt(test_order)
                return {'success': True, 'message': f'Test receipt generated: {temp_file}'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error printing test receipt: {str(e)}'}
    
    def open_test_drawer(self, drawer_name: str) -> Dict:
        """Open a specific cash drawer for testing"""
        try:
            drawer_info = self.cash_drawer_manager.get_drawer_status(drawer_name)
            if 'error' in drawer_info:
                return {'success': False, 'message': 'Cash drawer not found'}
            
            result = self.cash_drawer_manager.open_drawer(drawer_info)
            return result
            
        except Exception as e:
            return {'success': False, 'message': f'Error opening cash drawer: {str(e)}'}
    
    def get_hardware_status(self) -> Dict:
        """Get current status of all hardware"""
        return {
            'timestamp': datetime.now().isoformat(),
            'system_info': self.system_info,
            'printers': self.printer_manager.get_all_printers(),
            'cash_drawers': self.cash_drawer_manager.get_all_drawers(),
            'last_test': self.test_history[-1] if self.test_history else None
        }
    
    def get_test_history(self, limit: int = 10) -> List[Dict]:
        """Get test history"""
        return self.test_history[-limit:] if self.test_history else []
    
    def export_test_results(self, test_results: Dict, format: str = 'json') -> str:
        """Export test results in specified format"""
        if format.lower() == 'json':
            return json.dumps(test_results, indent=2, default=str)
        elif format.lower() == 'html':
            return self._generate_html_report(test_results)
        else:
            return json.dumps(test_results, indent=2, default=str)
    
    def _generate_html_report(self, test_results: Dict) -> str:
        """Generate HTML report for test results"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Hardware Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        .warning {{ color: orange; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Hardware Test Report</h1>
        <p>Generated: {test_results.get('test_time', 'Unknown')}</p>
        <p>System: {self.system_info.get('platform', 'Unknown')} {self.system_info.get('platform_release', '')}</p>
    </div>
    
    <div class="section">
        <h2>Summary</h2>
        <p>Status: <span class="{'success' if test_results.get('summary', {}).get('overall_status') == 'Success' else 'warning'}">
        {test_results.get('summary', {}).get('overall_status', 'Unknown')}</span></p>
        <p>Printers: {test_results.get('summary', {}).get('working_printers', 0)}/{test_results.get('summary', {}).get('total_printers', 0)} working</p>
        <p>Cash Drawers: {test_results.get('summary', {}).get('working_drawers', 0)}/{test_results.get('summary', {}).get('total_drawers', 0)} working</p>
    </div>
    
    <div class="section">
        <h2>Printer Tests</h2>
        <table>
            <tr><th>Printer</th><th>Connection</th><th>Print</th><th>Overall</th></tr>
"""
        
        for test in test_results.get('printer_tests', []):
            connection_status = test.get('tests', {}).get('connection', {}).get('success', False)
            print_status = test.get('tests', {}).get('print', {}).get('success', False)
            overall_status = test.get('overall_success', False)
            
            html += f"""
            <tr>
                <td>{test.get('printer_info', {}).get('name', 'Unknown')}</td>
                <td class="{'success' if connection_status else 'failure'}">{'✓' if connection_status else '✗'}</td>
                <td class="{'success' if print_status else 'failure'}">{'✓' if print_status else '✗'}</td>
                <td class="{'success' if overall_status else 'failure'}">{'✓' if overall_status else '✗'}</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
    
    <div class="section">
        <h2>Cash Drawer Tests</h2>
        <table>
            <tr><th>Drawer</th><th>Connection</th><th>Open</th><th>Overall</th></tr>
"""
        
        for test in test_results.get('cash_drawer_tests', []):
            connection_status = test.get('tests', {}).get('connection', {}).get('success', False)
            open_status = test.get('tests', {}).get('open', {}).get('success', False)
            overall_status = test.get('overall_success', False)
            
            html += f"""
            <tr>
                <td>{test.get('drawer_info', {}).get('name', 'Unknown')}</td>
                <td class="{'success' if connection_status else 'failure'}">{'✓' if connection_status else '✗'}</td>
                <td class="{'success' if open_status else 'failure'}">{'✓' if open_status else '✗'}</td>
                <td class="{'success' if overall_status else 'failure'}">{'✓' if overall_status else '✗'}</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        <ul>
"""
        
        for recommendation in test_results.get('summary', {}).get('recommendations', []):
            html += f"<li>{recommendation}</li>"
        
        html += """
        </ul>
    </div>
</body>
</html>
"""
        
        return html
    
    def save_test_results(self, test_results: Dict, filename: str = None) -> str:
        """Save test results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hardware_test_{timestamp}.json"
        
        try:
            filepath = os.path.join(current_app.instance_path, filename)
            with open(filepath, 'w') as f:
                json.dump(test_results, f, indent=2, default=str)
            return filepath
        except Exception as e:
            raise Exception(f"Failed to save test results: {str(e)}")