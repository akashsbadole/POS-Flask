"""
Receipt printing functionality for Restaurant POS System
Supports ESC/POS thermal printers and browser printing
"""

import os
from datetime import datetime
from flask import current_app
from app.models.order import Order, OrderItem, Payment
from app.models.menu import MenuItem, ItemVariant, AddOn

class ReceiptPrinter:
    """Receipt printing class supporting ESC/POS and browser printing"""
    
    def __init__(self, printer_device=None):
        self.printer_device = printer_device
        self.escpos_enabled = False
        
        # Try to initialize ESC/POS printer
        if printer_device:
            try:
                from escpos.printer import Usb
                self.printer = Usb(printer_device)
                self.escpos_enabled = True
            except ImportError:
                print("ESC/POS library not available, using browser printing")
            except Exception as e:
                print(f"Failed to initialize printer: {e}")
    
    def print_receipt(self, order):
        """Print receipt for order"""
        try:
            # Ensure we have a fresh order object with all relationships loaded
            from app import db
            order = db.session.merge(order)
            db.session.refresh(order)
            
            if self.escpos_enabled:
                self._print_escpos_receipt(order)
            else:
                self._generate_browser_receipt(order)
        except Exception as e:
            print(f"Error printing receipt: {e}")
            return False
        return True
    
    def _print_escpos_receipt(self, order):
        """Print receipt using ESC/POS commands"""
        try:
            # Set printer settings using raw commands
            self.printer._raw(b'\x1b\x61\x01')  # Center align
            
            # Print header
            self.printer._raw(b'\x1b\x21\x08')  # Double height
            self.printer.text('RESTAURANT POS\n')
            self.printer._raw(b'\x1b\x21\x00')  # Normal text
            self.printer.text('=' * 32 + '\n')
            self.printer.text('Receipt\n')
            self.printer.text('=' * 32 + '\n')
            
            # Print order details
            self.printer._raw(b'\x1b\x61\x00')  # Left align
            self.printer.text(f"Order: {order.order_number}\n")
            self.printer.text(f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n")
            self.printer.text(f"Cashier: {order.user.name}\n")
            self.printer.text('-' * 32 + '\n')
            
            # Print items
            items_list = list(order.items) if order.items else []
            for item in items_list:
                self._print_escpos_item(item)
            
            # Print totals
            self.printer.text('-' * 32 + '\n')
            self.printer.text(f"Subtotal: ${order.subtotal:.2f}\n")
            self.printer.text(f"Tax ({order.tax_rate*100:.1f}%): ${order.tax_amount:.2f}\n")
            self.printer._raw(b'\x1b\x21\x08')  # Double height for total
            self.printer.text(f"Total: ${order.total:.2f}\n")
            self.printer._raw(b'\x1b\x21\x00')  # Normal text
            
            # Print payment info
            payments_list = list(order.payments) if order.payments else []
            if payments_list:
                self.printer.text('-' * 32 + '\n')
                for payment in payments_list:
                    self.printer.text(f"Paid by: {payment.method.value}\n")
                    self.printer.text(f"Amount: ${payment.amount:.2f}\n")
            
            # Print footer
            self.printer.text('-' * 32 + '\n')
            self.printer.text('Thank you for your order!\n')
            self.printer.text('Please come again\n')
            
            # Cut paper
            self.printer.cut()
            
        except Exception as e:
            print(f"ESC/POS printing error: {e}")
            raise
    
    def _print_escpos_item(self, item):
        """Print individual item on ESC/POS receipt"""
        # Item name and quantity
        item_line = f"{item.quantity}x {item.menu_item.name}"
        if item.variant:
            item_line += f" ({item.variant.name})"
        
        self.printer.text(item_line + '\n')
        
        # Add-ons
        add_ons_list = list(item.add_ons) if item.add_ons else []
        if add_ons_list:
            for add_on in add_ons_list:
                self.printer.text(f"  + {add_on.name}: ${add_on.price:.2f}\n")
        
        # Price
        item_total = item.get_total_price()
        self.printer.text(f"${item_total:.2f}\n")
    
    def _generate_browser_receipt(self, order):
        """Generate HTML receipt for browser printing"""
        # Ensure we have a fresh order object with all relationships loaded
        from app import db
        order = db.session.merge(order)
        db.session.refresh(order)
        
        receipt_html = self._get_receipt_html(order)
        
        # Save to temporary file
        temp_file = os.path.join(current_app.instance_path, f'receipt_{order.id}.html')
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(receipt_html)
        
        return temp_file
    
    def _get_receipt_html(self, order):
        """Generate HTML receipt content"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Receipt - Order {order.order_number}</title>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            max-width: 400px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px dashed #000;
            padding-bottom: 10px;
            margin-bottom: 10px;
        }}
        .item {{
            margin-bottom: 5px;
        }}
        .total {{
            border-top: 2px dashed #000;
            padding-top: 10px;
            margin-top: 10px;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
        }}
        @media print {{
            body {{
                margin: 0;
                padding: 10px;
            }}
            .no-print {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>RESTAURANT POS</h2>
        <p>Receipt</p>
    </div>
    
    <div class="order-info">
        <p><strong>Order:</strong> {order.order_number}</p>
        <p><strong>Date:</strong> {order.created_at.strftime('%Y-%m-%d %H:%M')}</p>
        <p><strong>Cashier:</strong> {order.user.name}</p>
        {order.table_id and f"<p><strong>Table:</strong> {order.table.number}</p>"}
    </div>
    
    <div class="items">
        {self._get_items_html(order.items)}
    </div>
    
    <div class="total">
        <p><strong>Subtotal:</strong> ${order.subtotal:.2f}</p>
        <p><strong>Tax ({order.tax_rate*100:.1f}%):</strong> ${order.tax_amount:.2f}</p>
        <p><strong>Total:</strong> ${order.total:.2f}</p>
        
        {order.payments and self._get_payments_html(order.payments)}
    </div>
    
    <div class="footer">
        <p>Thank you for your order!</p>
        <p>Please come again</p>
        <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <script>
        // Auto-print when loaded
        window.onload = function() {{
            setTimeout(function() {{
                window.print();
            }}, 500);
        }};
    </script>
</body>
</html>
        """
    
    def _get_items_html(self, items):
        """Generate HTML for order items"""
        html = ""
        for item in items:
            html += f"""
            <div class="item">
                <p>{item.quantity}x {item.menu_item.name}</p>
                {item.variant and f"<p>&nbsp;&nbsp;&nbsp;({item.variant.name})</p>"}
                {item.add_ons and self._get_addons_html(item.add_ons)}
                <p style="text-align: right;">${item.get_total_price():.2f}</p>
            </div>
            """
        return html
    
    def _get_addons_html(self, add_ons):
        """Generate HTML for item add-ons"""
        html = ""
        for add_on in add_ons:
            html += f"<p>&nbsp;&nbsp;&nbsp;+ {add_on.name}: ${add_on.price:.2f}</p>"
        return html
    
    def _get_payments_html(self, payments):
        """Generate HTML for payment information"""
        html = ""
        for payment in payments:
            html += f"""
                <p><strong>Payment Method:</strong> {payment.method.value}</p>
                <p><strong>Amount:</strong> ${payment.amount:.2f}</p>
                """
        return html

def print_kitchen_ticket(order):
    """Print kitchen ticket for order"""
    printer = ReceiptPrinter()
    
    try:
        # Ensure we have a fresh order object with all relationships loaded
        from app import db
        order = db.session.merge(order)
        db.session.refresh(order)
        
        if printer.escpos_enabled:
            printer.printer._raw(b'\x1b\x61\x01')  # Center align
            printer.printer._raw(b'\x1b\x21\x08')  # Double height
            printer.printer.text('KITCHEN TICKET\n')
            printer.printer._raw(b'\x1b\x21\x00')  # Normal text
            printer.printer.text('=' * 32 + '\n')
            printer.printer.text(f'Order: {order.order_number}\n')
            printer.printer.text(f'Table: {order.table.number if order.table else "Takeaway"}\n')
            printer.printer.text(f'Time: {order.created_at.strftime("%H:%M")}\n')
            printer.printer.text('-' * 32 + '\n')
            
            # Print items
            printer.printer._raw(b'\x1b\x61\x00')  # Left align
            items_list = list(order.items) if order.items else []
            for item in items_list:
                item_line = f"{item.quantity}x {item.menu_item.name}"
                if item.notes:
                    item_line += f" ({item.notes})"
                printer.printer.text(item_line + '\n')
            
            printer.printer.text('-' * 32 + '\n')
            printer.printer.text(f'Prep time: {order.created_at.strftime("%H:%M")}\n')
            printer.printer.cut()
        else:
            # Generate kitchen ticket HTML
            ticket_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Kitchen Ticket - Order {order.order_number}</title>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            max-width: 400px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px dashed #000;
            padding-bottom: 10px;
            margin-bottom: 10px;
        }}
        .item {{
            margin-bottom: 5px;
            font-size: 14px;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-weight: bold;
        }}
        @media print {{
            body {{
                margin: 0;
                padding: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>KITCHEN TICKET</h2>
        <p>Order: {order.order_number}</p>
        <p>Table: {order.table.number if order.table else "Takeaway"}</p>
        <p>Time: {order.created_at.strftime("%H:%M")}</p>
    </div>
    
    <div class="items">
        {"".join([f'<div class="item">{item.quantity}x {item.menu_item.name}{item.notes and f" ({item.notes})"}</div>' for item in order.items])}
    </div>
    
    <div class="footer">
        <p>Prep time: {order.created_at.strftime("%H:%M")}</p>
    </div>
    
    <script>
        setTimeout(function() {{
            window.print();
        }}, 500);
    </script>
</body>
</html>
            """
            
            # Save to temporary file
            temp_file = os.path.join(current_app.instance_path, f'kitchen_ticket_{order.id}.html')
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(ticket_html)
            
            return temp_file
            
    except Exception as e:
        print(f"Error printing kitchen ticket: {e}")
        return None

def open_cash_drawer():
    """Send command to open cash drawer via printer"""
    printer = ReceiptPrinter()
    
    try:
        if printer.escpos_enabled:
            # Send cash drawer pulse command (ESC/POS specific)
            printer.printer._raw(b'\x1B\x70\x00\x19\xFF')
        else:
            print("Cash drawer command not available without ESC/POS printer")
        return True
    except Exception as e:
        print(f"Error opening cash drawer: {e}")
        return False