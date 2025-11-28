"""
Cash drawer management module for Restaurant POS System
Supports various cash drawer interfaces
"""

import platform
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from app.receipt_printer import ReceiptPrinter


class CashDrawerManager:
    """Enhanced cash drawer management with device detection and testing"""
    
    def __init__(self):
        self.available_drawers = []
        self.current_drawer = None
        self.drawer_status = {}
        self._detect_drawers()
    
    def _detect_drawers(self):
        """Detect available cash drawers"""
        try:
            # Detect ESC/POS connected cash drawers
            self._detect_escpos_drawers()
            
            # Detect serial port cash drawers
            self._detect_serial_drawers()
            
            # Detect USB cash drawers
            self._detect_usb_drawers()
            
        except Exception as e:
            print(f"Error detecting cash drawers: {e}")
    
    def _detect_escpos_drawers(self):
        """Detect cash drawers connected via ESC/POS printers"""
        try:
            # Try to detect through receipt printer
            printer = ReceiptPrinter()
            if printer.escpos_enabled:
                self.available_drawers.append({
                    'name': 'ESC/POS Cash Drawer',
                    'device_id': 'escpos_printer',
                    'connection_type': 'ESC/POS Printer',
                    'port': 'Printer Port',
                    'status': 'Connected',
                    'type': 'ESC/POS'
                })
        except Exception as e:
            print(f"ESC/POS drawer detection failed: {e}")
    
    def _detect_serial_drawers(self):
        """Detect serial port cash drawers"""
        try:
            import serial.tools.list_ports
            
            ports = serial.tools.list_ports.comports()
            for port in ports:
                # Common cash drawer device identifiers
                if any(keyword in port.description.lower() for keyword in 
                      ['cash drawer', 'drawer', 'pos', 'thermal', 'epson', 'star']):
                    self.available_drawers.append({
                        'name': f"Serial Cash Drawer ({port.device})",
                        'device_id': port.device,
                        'connection_type': 'Serial',
                        'port': port.device,
                        'status': 'Connected',
                        'type': 'Serial',
                        'description': port.description
                    })
        except ImportError:
            print("PySerial library not available")
        except Exception as e:
            print(f"Serial drawer detection failed: {e}")
    
    def _detect_usb_drawers(self):
        """Detect USB cash drawers"""
        try:
            import usb.core
            import usb.util
            
            # Common cash drawer vendor IDs
            cash_drawer_vendors = [
                0x04b8,  # Epson
                0x154f,  # POS
                0x1c86,  # Star Micronics
                0x0fe6,  # Custom (China)
                0x0483,  # STMicroelectronics
            ]
            
            devices = usb.core.find(find_all=True)
            
            for device in devices:
                if device.idVendor in cash_drawer_vendors:
                    try:
                        manufacturer = usb.util.get_string(device, device.iManufacturer) or "Unknown"
                        product = usb.util.get_string(device, device.iProduct) or "Unknown"
                        
                        self.available_drawers.append({
                            'name': f"USB Cash Drawer ({manufacturer} {product})",
                            'device_id': f"{device.idVendor:04x}:{device.idProduct:04x}",
                            'connection_type': 'USB',
                            'port': f"USB {device.bus}-{device.address}",
                            'status': 'Connected',
                            'type': 'USB',
                            'vendor_id': device.idVendor,
                            'product_id': device.idProduct
                        })
                    except Exception as e:
                        print(f"Error getting USB device info: {e}")
                        
        except ImportError:
            print("USB library not available")
        except Exception as e:
            print(f"USB drawer detection failed: {e}")
    
    def test_cash_drawer(self, drawer_info: Dict) -> Dict:
        """Test a specific cash drawer"""
        test_result = {
            'drawer_name': drawer_info.get('name', 'Unknown'),
            'test_time': datetime.now().isoformat(),
            'tests': {}
        }
        
        try:
            if drawer_info.get('type') == 'ESC/POS':
                test_result['tests']['connection'] = self._test_escpos_connection(drawer_info)
                test_result['tests']['open'] = self._test_escpos_open(drawer_info)
            elif drawer_info.get('type') == 'Serial':
                test_result['tests']['connection'] = self._test_serial_connection(drawer_info)
                test_result['tests']['open'] = self._test_serial_open(drawer_info)
            elif drawer_info.get('type') == 'USB':
                test_result['tests']['connection'] = self._test_usb_connection(drawer_info)
                test_result['tests']['open'] = self._test_usb_open(drawer_info)
            else:
                test_result['tests']['connection'] = {'success': False, 'message': 'Unsupported drawer type'}
                test_result['tests']['open'] = {'success': False, 'message': 'Unsupported drawer type'}
                
        except Exception as e:
            test_result['error'] = str(e)
        
        return test_result
    
    def _test_escpos_connection(self, drawer_info: Dict) -> Dict:
        """Test ESC/POS cash drawer connection"""
        try:
            printer = ReceiptPrinter()
            if printer.escpos_enabled:
                return {'success': True, 'message': 'ESC/POS printer connected'}
            else:
                return {'success': False, 'message': 'ESC/POS printer not available'}
        except Exception as e:
            return {'success': False, 'message': f'Connection failed: {str(e)}'}
    
    def _test_escpos_open(self, drawer_info: Dict) -> Dict:
        """Test opening ESC/POS cash drawer"""
        try:
            from app.receipt_printer import open_cash_drawer
            result = open_cash_drawer()
            if result:
                return {'success': True, 'message': 'Cash drawer opened successfully'}
            else:
                return {'success': False, 'message': 'Failed to open cash drawer'}
        except Exception as e:
            return {'success': False, 'message': f'Open test failed: {str(e)}'}
    
    def _test_serial_connection(self, drawer_info: Dict) -> Dict:
        """Test serial cash drawer connection"""
        try:
            import serial
            
            port = drawer_info.get('port')
            if not port:
                return {'success': False, 'message': 'Invalid port'}
            
            # Try to open serial port
            ser = serial.Serial(port, baudrate=9600, timeout=1)
            ser.close()
            
            return {'success': True, 'message': 'Serial port accessible'}
            
        except ImportError:
            return {'success': False, 'message': 'PySerial library not available'}
        except Exception as e:
            return {'success': False, 'message': f'Serial connection failed: {str(e)}'}
    
    def _test_serial_open(self, drawer_info: Dict) -> Dict:
        """Test opening serial cash drawer"""
        try:
            import serial
            
            port = drawer_info.get('port')
            if not port:
                return {'success': False, 'message': 'Invalid port'}
            
            # Open serial port and send open command
            ser = serial.Serial(port, baudrate=9600, timeout=1)
            
            # Common cash drawer open commands
            open_commands = [
                b'\x1B\x70\x00\x19\xFF',  # ESC/POS cash drawer kick
                b'\x1B\x70\x01\x19\xFF',  # Alternative ESC/POS
                b'\x0A',                 # Line feed (sometimes opens drawer)
                b'\x07',                 # Bell (sometimes opens drawer)
            ]
            
            for command in open_commands:
                ser.write(command)
                ser.flush()
            
            ser.close()
            
            return {'success': True, 'message': 'Open command sent to serial drawer'}
            
        except Exception as e:
            return {'success': False, 'message': f'Serial open test failed: {str(e)}'}
    
    def _test_usb_connection(self, drawer_info: Dict) -> Dict:
        """Test USB cash drawer connection"""
        try:
            import usb.core
            
            vendor_id = drawer_info.get('vendor_id')
            product_id = drawer_info.get('product_id')
            
            if not vendor_id or not product_id:
                return {'success': False, 'message': 'Invalid USB device info'}
            
            device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
            if device:
                return {'success': True, 'message': 'USB cash drawer found'}
            else:
                return {'success': False, 'message': 'USB cash drawer not found'}
                
        except ImportError:
            return {'success': False, 'message': 'USB library not available'}
        except Exception as e:
            return {'success': False, 'message': f'USB connection failed: {str(e)}'}
    
    def _test_usb_open(self, drawer_info: Dict) -> Dict:
        """Test opening USB cash drawer"""
        try:
            import usb.core
            
            vendor_id = drawer_info.get('vendor_id')
            product_id = drawer_info.get('product_id')
            
            device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
            if device:
                # Try to send control transfer to open drawer
                # This is device-specific and may need customization
                try:
                    device.ctrl_transfer(
                        bmRequestType=0x21,  # Host to device, class, interface
                        bRequest=0x09,      # SET_REPORT
                        wValue=0x0200,       # Report type and ID
                        wIndex=0x00,         # Interface
                        data_or_wLength=b'\x1B\x70\x00\x19\xFF'  # ESC/POS open command
                    )
                    return {'success': True, 'message': 'USB cash drawer opened'}
                except Exception as e:
                    return {'success': False, 'message': f'USB control transfer failed: {str(e)}'}
            else:
                return {'success': False, 'message': 'USB cash drawer not found'}
                
        except Exception as e:
            return {'success': False, 'message': f'USB open test failed: {str(e)}'}
    
    def open_drawer(self, drawer_info: Dict) -> Dict:
        """Open a specific cash drawer"""
        try:
            if drawer_info.get('type') == 'ESC/POS':
                from app.receipt_printer import open_cash_drawer
                result = open_cash_drawer()
                return {'success': result, 'message': 'ESC/POS drawer opened' if result else 'Failed to open ESC/POS drawer'}
            
            elif drawer_info.get('type') == 'Serial':
                return self._open_serial_drawer(drawer_info)
            
            elif drawer_info.get('type') == 'USB':
                return self._open_usb_drawer(drawer_info)
            
            else:
                return {'success': False, 'message': 'Unsupported drawer type'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error opening drawer: {str(e)}'}
    
    def _open_serial_drawer(self, drawer_info: Dict) -> Dict:
        """Open serial cash drawer"""
        try:
            import serial
            
            port = drawer_info.get('port')
            if not port:
                return {'success': False, 'message': 'Invalid port'}
            
            ser = serial.Serial(port, baudrate=9600, timeout=1)
            ser.write(b'\x1B\x70\x00\x19\xFF')  # ESC/POS cash drawer kick
            ser.flush()
            ser.close()
            
            return {'success': True, 'message': 'Serial drawer opened'}
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to open serial drawer: {str(e)}'}
    
    def _open_usb_drawer(self, drawer_info: Dict) -> Dict:
        """Open USB cash drawer"""
        try:
            import usb.core
            
            vendor_id = drawer_info.get('vendor_id')
            product_id = drawer_info.get('product_id')
            
            device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
            if device:
                device.ctrl_transfer(
                    bmRequestType=0x21,
                    bRequest=0x09,
                    wValue=0x0200,
                    wIndex=0x00,
                    data_or_wLength=b'\x1B\x70\x00\x19\xFF'
                )
                return {'success': True, 'message': 'USB drawer opened'}
            else:
                return {'success': False, 'message': 'USB drawer not found'}
                
        except Exception as e:
            return {'success': False, 'message': f'Failed to open USB drawer: {str(e)}'}
    
    def get_drawer_status(self, drawer_name: str) -> Dict:
        """Get current status of a specific cash drawer"""
        for drawer in self.available_drawers:
            if drawer['name'] == drawer_name:
                return drawer
        return {'error': 'Cash drawer not found'}
    
    def set_default_drawer(self, drawer_name: str) -> bool:
        """Set default cash drawer"""
        for drawer in self.available_drawers:
            if drawer['name'] == drawer_name:
                self.current_drawer = drawer
                return True
        return False
    
    def get_all_drawers(self) -> List[Dict]:
        """Get all available cash drawers"""
        return self.available_drawers.copy()
    
    def get_drawer_logs(self, drawer_name: str = None) -> List[Dict]:
        """Get logs for cash drawer operations"""
        # This would typically read from a log file or database
        # For now, return mock data
        return [
            {
                'timestamp': datetime.now().isoformat(),
                'drawer': drawer_name or 'Default',
                'action': 'open',
                'user': 'Test User',
                'success': True,
                'message': 'Cash drawer opened successfully'
            }
        ]