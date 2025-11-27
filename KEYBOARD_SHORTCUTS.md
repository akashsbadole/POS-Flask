# Keyboard Navigation and Accessibility Guide

This document outlines all keyboard shortcuts and accessibility features implemented in the Restaurant POS system.

## Table of Contents
- [Global Shortcuts](#global-shortcuts)
- [Navigation Shortcuts](#navigation-shortcuts)
- [Form Shortcuts](#form-shortcuts)
- [Billing Shortcuts](#billing-shortcuts)
- [Cart & Payment Shortcuts](#cart--payment-shortcuts)
- [Accessibility Features](#accessibility-features)
- [Testing](#testing)

## Global Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl + /` | Show Help | Display keyboard shortcuts help modal |
| `Ctrl + K` | Focus Search | Move focus to global search bar |
| `Escape` | Escape Action | Close modals, dropdowns, cancel actions |
| `Ctrl + N` | Toggle Notifications | Open/close notifications panel |
| `Ctrl + B` | Toggle Sidebar | Show/hide navigation sidebar |

## Navigation Shortcuts

| Shortcut | Action | Target |
|----------|--------|---------|
| `Alt + 1` | Dashboard/Cashier/Kitchen | Main dashboard or role-specific home |
| `Alt + 2` | Menu Management | Navigate to menu items |
| `Alt + 3` | Table Management | Navigate to table management |
| `Alt + 4` | Reports | Navigate to reports section |
| `Alt + 5` | Inventory | Navigate to inventory management |
| `Alt + 6` | Billing | Navigate to billing/invoices |
| `Alt + 7` | Settings | Navigate to system settings |
| `Alt + 8` | System Status | Navigate to system status page |
| `Alt + P` | User Profile | Navigate to user profile |
| `Alt + L` | Logout | Logout from system |

## Form Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Tab` | Next Field | Move to next form field |
| `Shift + Tab` | Previous Field | Move to previous form field |
| `Ctrl + S` | Save Form | Save current form data |
| `Ctrl + Enter` | Submit Form | Submit current form |
| `Enter` | Confirm Action | Confirm buttons, dialogs |
| `Space` | Activate/Select | Toggle checkboxes, activate buttons |

### Field-Specific Access Keys

| Field Type | Access Key | Example |
|-------------|-------------|----------|
| Name fields | `N` | Customer Name, Item Name |
| Email fields | `E` | Customer Email |
| Password fields | `P` | Login Password |
| Phone fields | `P` | Customer Phone |
| Address fields | `A` | Customer Address |
| Description fields | `D` | Item Description |
| Price fields | `P` | Item Price |
| Category fields | `C` | Item Category |
| Date fields | `I/D` | Issue/Due dates |
| Time fields | `T` | Preparation time |
| Method fields | `M` | Payment method |
| Amount fields | `A` | Payment amount |

## Billing Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl + I` | New Invoice | Create new invoice |
| `Ctrl + Shift + I` | Invoice List | View all invoices |
| `Ctrl + Shift + V` | View Invoice | View current invoice |
| `Ctrl + Shift + E` | Edit Invoice | Edit current invoice |
| `Ctrl + Shift + D` | Delete Invoice | Delete current invoice |
| `Ctrl + P` | Print Receipt | Print current receipt/invoice |
| `Ctrl + Shift + R` | Recurring Invoice | Create recurring invoice |
| `Ctrl + Shift + S` | Invoice Settings | Open billing settings |
| `Ctrl + Shift + T` | Generate Report | Generate billing report |
| `Ctrl + D` | Add Discount | Open discount modal |
| `Ctrl + Shift + P` | Split Payment | Open split payment form |

## Order Management Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl + O` | Order List | View all orders |
| `Ctrl + Shift + O` | Create Order | Create new order |

## Cart & Payment Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl + C` | View Cart | Focus on cart indicator |
| `Ctrl + Plus` | Add to Cart | Add selected item to cart |
| `Ctrl + Minus` | Remove from Cart | Remove selected item |
| `F1` | Quick Cash | Set payment to cash |
| `F2` | Quick Card | Set payment to card |
| `F3` | Quick UPI | Set payment to UPI |

## Accessibility Features

### Screen Reader Support
- **ARIA Labels**: All interactive elements have descriptive ARIA labels
- **Live Regions**: Dynamic content updates announced via live regions
- **Role Attributes**: Proper semantic roles for navigation, main content, forms
- **Descriptive Links**: Link text describes destination clearly

### Keyboard Navigation
- **Tab Order**: Logical tab order through all interactive elements
- **Focus Indicators**: Clear visual focus indicators with high contrast
- **Skip Links**: Skip to main content link for keyboard users
- **Focus Trapping**: Focus trapped within modals for better navigation

### Visual Accessibility
- **High Contrast**: Support for high contrast mode
- **Reduced Motion**: Respects prefers-reduced-motion setting
- **Focus Styles**: Enhanced focus outlines for better visibility
- **Large Text**: Support for text scaling

### Cognitive Accessibility
- **Consistent Navigation**: Predictable navigation patterns
- **Clear Labels**: Form fields clearly labeled
- **Error Messages**: Accessible error announcements
- **Help System**: Built-in keyboard shortcuts help

## Testing

### Automated Testing
The system includes an automated accessibility tester that checks for:
- Proper ARIA implementation
- Keyboard accessibility
- Screen reader compatibility
- Form accessibility
- Focus management

### Manual Testing Checklist

#### Keyboard Navigation
- [ ] Can navigate entire interface using Tab
- [ ] All interactive elements reachable by keyboard
- [ ] Clear focus indicators on all elements
- [ ] Logical tab order
- [ ] Escape key works to close modals/dropdowns

#### Screen Reader
- [ ] All images have alt text
- [ ] Form fields properly labeled
- [ ] Dynamic content announced
- [ ] Navigation landmarks present
- [ ] Error messages accessible

#### Visual Accessibility
- [ ] Sufficient color contrast (4.5:1 minimum)
- [ ] Text resizable to 200%
- [ ] Interface usable without color
- [ ] No content flashes

### Running Tests

To run accessibility tests:

1. **In Browser Console**:
   ```javascript
   runAccessibilityTests()
   ```

2. **Test Keyboard Shortcuts**:
   ```javascript
   testKeyboardShortcuts()
   ```

3. **Manual Testing**:
   - Use only keyboard to navigate the entire application
   - Test with screen reader software
   - Use accessibility testing tools

## Browser Compatibility

### Supported Browsers
- **Chrome**: Full support
- **Firefox**: Full support  
- **Safari**: Full support
- **Edge**: Full support

### Required Features
- JavaScript enabled
- Modern CSS support
- ARIA support

## Implementation Details

### Files Modified
- `app/templates/base.html` - Main navigation and accessibility
- `app/templates/auth/login.html` - Login form accessibility
- `app/templates/billing/invoice_form.html` - Billing form shortcuts
- `app/templates/orders/checkout.html` - Payment form accessibility
- `app/templates/menu/item_form.html` - Menu form accessibility
- `app/static/js/keyboard-navigation.js` - Core keyboard navigation
- `app/static/js/accessibility-test.js` - Accessibility testing suite

### Key Features Implemented

#### Keyboard Navigation System
- Comprehensive shortcut system
- Context-aware navigation
- Focus management
- Modal trapping
- Help system

#### Accessibility Enhancements
- ARIA labeling
- Screen reader support
- High contrast mode
- Reduced motion support
- Skip links
- Focus indicators

#### Form Enhancements
- Access keys on all fields
- Validation feedback
- Error announcements
- Logical tab order
- Clear labels

## Troubleshooting

### Common Issues

**Keyboard shortcuts not working**
- Check if JavaScript is enabled
- Ensure focus is on the correct element
- Try refreshing the page

**Screen reader not announcing updates**
- Check if ARIA live regions are present
- Verify screen reader is in correct mode
- Test with different screen readers

**Focus indicators not visible**
- Check custom CSS is loaded
- Verify high contrast mode settings
- Test with different browsers

### Getting Help

For accessibility issues:
1. Press `Ctrl + /` to see available shortcuts
2. Run `runAccessibilityTests()` in browser console
3. Contact support with browser and assistive technology details

## Future Enhancements

### Planned Features
- Voice control integration
- Touch gesture support
- Additional screen reader optimizations
- Customizable keyboard shortcuts
- Advanced color themes

### Feedback
Please provide feedback on accessibility features to help improve the system for all users.