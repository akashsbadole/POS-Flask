"""
Printer management module for Restaurant POS System
Supports ESC/POS thermal printers and browser printing
"""

import os
import platform
import subprocess
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from flask import current_app
from app.receipt_printer import ReceiptPrinter


class PrinterManager:
    """Enhanced printer management with device detection and testing"""
    
    def __init__(self):
        self.available_printers = []
        self.current_printer = None
        self.printer_status = {}
        self._detect_printers()
    
    def _detect_printers(self):
        """Detect available printers on the system"""
        try:
            system = platform.system()
            
            if system == "Windows":
                self._detect_windows_printers()
            elif system == "Linux":
                self._detect_linux_printers()
            elif system == "Darwin":  # macOS
                self._detect_macos_printers()
                
        except Exception as e:
            print(f"Error detecting printers: {e}")
    
    def _detect_windows_printers(self):
        """Detect printers on Windows using WMI"""
        try:
            import wmi
            c = wmi.WMI()
            
            for printer in c.Win32_Printer():
                if printer.Status == 3:  # Printer is ready
                    self.available_printers.append({
                        'name': printer.Name,
                        'device_id': printer.DeviceID,
                        'port': printer.PortName,
                        'driver': printer.DriverName,
                        'status': 'Ready',
                        'type': 'Windows Printer'
                    })
                    
        except ImportError:
            # Fallback to basic detection
            try:
                result = subprocess.run(['wmic', 'printer', 'get', 'name', '/format:list'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n\n')
                    for line in lines:
                        if '=' in line:
                            name = line.split('=')[1].strip()
                            if name:
                                self.available_printers.append({
                                    'name': name,
                                    'device_id': name,
                                    'port': 'Unknown',
                                    'driver': 'Unknown',
                                    'status': 'Unknown',
                                    'type': 'Windows Printer'
                                })
            except Exception as e:
                print(f"Windows printer detection failed: {e}")
    
    def _detect_linux_printers(self):
        """Detect printers on Linux using lpstat"""
        try:
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.startswith('printer'):
                        parts = line.split()
                        if len(parts) >= 2:
                            name = parts[1]
                            status = 'Enabled' if 'enabled' in line.lower() else 'Disabled'
                            self.available_printers.append({
                                'name': name,
                                'device_id': name,
                                'port': 'Unknown',
                                'driver': 'Unknown',
                                'status': status,
                                'type': 'CUPS Printer'
                            })
        except Exception as e:
            print(f"Linux printer detection failed: {e}")
    
    def _detect_macos_printers(self):
        """Detect printers on macOS using lpstat"""
        try:
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.startswith('printer'):
                        parts = line.split()
                        if len(parts) >= 2:
                            name = parts[1]
                            status = 'Enabled' if 'enabled' in line.lower() else 'Disabled'
                            self.available_printers.append({
                                'name': name,
                                'device_id': name,
                                'port': 'Unknown',
                                'driver': 'Unknown',
                                'status': status,
                                'type': 'CUPS Printer'
                            })
        except Exception as e:
            print(f"macOS printer detection failed: {e}")
    
    def detect_usb_printers(self) -> List[Dict]:
        """Detect USB ESC/POS printers"""
        usb_printers = []
        
        try:
            import usb.core
            import usb.util
            
            # ESC/POS vendor IDs (common manufacturers)
            escpos_vendors = [
                0x04b8,  # Epson
                0x154f,  # POS
                0x1c86,  # Star Micronics
                0x0fe6,  # Custom (China)
                0x0483,  # STMicroelectronics
                0x1b1f,  # Custom
            ]
            
            devices = usb.core.find(find_all=True)
            
            for device in devices:
                if device.idVendor in escpos_vendors:
                    try:
                        manufacturer = usb.util.get_string(device, device.iManufacturer) or "Unknown"
                        product = usb.util.get_string(device, device.iProduct) or "Unknown"
                        
                        usb_printers.append({
                            'name': f"{manufacturer} {product}",
                            'device_id': f"{device.idVendor:04x}:{device.idProduct:04x}",
                            'vendor_id': device.idVendor,
                            'product_id': device.idProduct,
                            'port': f"USB {device.bus}-{device.address}",
                            'driver': 'ESC/POS',
                            'status': 'Connected',
                            'type': 'USB ESC/POS Printer'
                        })
                    except Exception as e:
                        print(f"Error getting USB device info: {e}")
                        
        except ImportError:
            print("USB library not available")
        except Exception as e:
            print(f"USB printer detection failed: {e}")
        
        return usb_printers
    
    def test_printer(self, printer_info: Dict) -> Dict:
        """Test a specific printer"""
        test_result = {
            'printer_name': printer_info.get('name', 'Unknown'),
            'test_time': datetime.now().isoformat(),
            'tests': {}
        }
        
        try:
            if printer_info.get('type') == 'USB ESC/POS Printer':
                test_result['tests']['connection'] = self._test_usb_printer(printer_info)
                test_result['tests']['print'] = self._test_usb_print(printer_info)
            else:
                test_result['tests']['connection'] = self._test_system_printer(printer_info)
                test_result['tests']['print'] = self._test_system_print(printer_info)
                
        except Exception as e:
            test_result['error'] = str(e)
        
        return test_result
    
    def _test_usb_printer(self, printer_info: Dict) -> Dict:
        """Test USB printer connection"""
        try:
            from escpos.printer import Usb
            
            vendor_id = printer_info.get('vendor_id')
            product_id = printer_info.get('product_id')
            
            if not vendor_id or not product_id:
                return {'success': False, 'message': 'Invalid USB device info'}
            
            printer = Usb(vendor_id, product_id)
            printer._raw(b'\x1b\x40')  # Initialize printer
            
            return {'success': True, 'message': 'USB printer connected successfully'}
            
        except ImportError:
            return {'success': False, 'message': 'ESC/POS library not available'}
        except Exception as e:
            return {'success': False, 'message': f'Connection failed: {str(e)}'}
    
    def _test_usb_print(self, printer_info: Dict) -> Dict:
        """Test USB printer printing"""
        try:
            from escpos.printer import Usb
            
            vendor_id = printer_info.get('vendor_id')
            product_id = printer_info.get('product_id')
            
            printer = Usb(vendor_id, product_id)
            
            # Print test page
            printer._raw(b'\x1b\x61\x01')  # Center align
            printer._raw(b'\x1b\x21\x08')  # Double height
            printer.text('PRINTER TEST\n')
            printer._raw(b'\x1b\x21\x00')  # Normal text
            printer.text('=' * 32 + '\n')
            printer.text(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            printer.text(f'Printer: {printer_info.get("name", "Unknown")}\n')
            printer.text('=' * 32 + '\n')
            printer.text('Test completed successfully!\n')
            printer.cut()
            
            return {'success': True, 'message': 'Test page printed successfully'}
            
        except Exception as e:
            return {'success': False, 'message': f'Print failed: {str(e)}'}
    
    def _test_system_printer(self, printer_info: Dict) -> Dict:
        """Test system printer connection"""
        try:
            printer_name = printer_info.get('name')
            
            if platform.system() == "Windows":
                result = subprocess.run(['wmic', 'printer', 'where', f'name="{printer_name}"', 'get', 'status'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and 'Ready' in result.stdout:
                    return {'success': True, 'message': 'Printer is ready'}
            else:
                result = subprocess.run(['lpstat', '-p', printer_name], capture_output=True, text=True)
                if result.returncode == 0 and 'enabled' in result.stdout.lower():
                    return {'success': True, 'message': 'Printer is enabled'}
            
            return {'success': False, 'message': 'Printer not ready'}
            
        except Exception as e:
            return {'success': False, 'message': f'Connection test failed: {str(e)}'}
    
    def _test_system_print(self, printer_info: Dict) -> Dict:
        """Test system printer printing"""
        try:
            printer_name = printer_info.get('name')
            
            # Create a simple test file
            test_content = f"""
Printer Test Page
================
Printer: {printer_name}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Status: Test completed successfully!
            """.strip()
            
            if platform.system() == "Windows":
                # Use Windows printing
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(test_content)
                    temp_file = f.name
                
                try:
                    subprocess.run(['notepad', '/p', temp_file], check=True)
                    return {'success': True, 'message': 'Test page sent to printer'}
                finally:
                    os.unlink(temp_file)
            else:
                # Use CUPS
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(test_content)
                    temp_file = f.name
                
                try:
                    subprocess.run(['lp', '-d', printer_name, temp_file], check=True)
                    return {'success': True, 'message': 'Test page sent to printer'}
                finally:
                    os.unlink(temp_file)
            
        except Exception as e:
            return {'success': False, 'message': f'Print test failed: {str(e)}'}
    
    def get_printer_status(self, printer_name: str) -> Dict:
        """Get current status of a specific printer"""
        for printer in self.available_printers:
            if printer['name'] == printer_name:
                return printer
        return {'error': 'Printer not found'}
    
    def set_default_printer(self, printer_name: str) -> bool:
        """Set the default printer"""
        for printer in self.available_printers:
            if printer['name'] == printer_name:
                self.current_printer = printer
                return True
        return False
    
    def get_all_printers(self) -> List[Dict]:
        """Get all available printers including USB ESC/POS"""
        all_printers = self.available_printers.copy()
        
        # Add USB ESC/POS printers
        usb_printers = self.detect_usb_printers()
        all_printers.extend(usb_printers)
        
        return all_printers
    
    def create_test_receipt(self) -> Dict:
        """Create a test order for receipt printing"""
        from app.models.order import Order, OrderItem, Payment, PaymentMethod
        from app.models.menu import MenuItem
        from app.models.user import User
        
        # Create a mock order for testing
        test_order = type('TestOrder', (), {
            'id': 999,
            'order_number': 'TEST-001',
            'created_at': datetime.now(),
            'user': type('TestUser', (), {'name': 'Test Cashier'})(),
            'table': type('TestTable', (), {'number': '1'})(),
            'subtotal': 25.50,
            'tax_amount': 2.24,
            'tax_rate': 0.0875,
            'total': 27.74,
            'items': [
                type('TestItem', (), {
                    'quantity': 2,
                    'menu_item': type('TestMenuItem', (), {'name': 'Test Burger'})(),
                    'variant': None,
                    'add_ons': [],
                    'get_total_price': lambda: 15.98
                })(),
                type('TestItem', (), {
                    'quantity': 1,
                    'menu_item': type('TestMenuItem', (), {'name': 'Test Fries'})(),
                    'variant': None,
                    'add_ons': [],
                    'get_total_price': lambda: 4.99
                })(),
                type('TestItem', (), {
                    'quantity': 1,
                    'menu_item': type('TestMenuItem', (), {'name': 'Test Drink'})(),
                    'variant': None,
                    'add_ons': [],
                    'get_total_price': lambda: 4.53
                })()
            ],
            'payments': [
                type('TestPayment', (), {
                    'method': type('TestMethod', (), {'value': 'cash'})(),
                    'amount': 27.74
                })()
            ]
        })()
        
        return test_order