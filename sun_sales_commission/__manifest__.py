{
    'name': 'Sales Commission for sales agent on Saleorder confim/Invoice validate time/Invoice Paid time',
    'version': '11.0.3',
    'category': 'Sales Management',
    'summary': 'This module you can assign commission to sales agent based on Sales order Confirmation, Validate invoice time, Invoice Paid time.',
    'depends': ['base','sale_management'],
    'price': 25,
    'currency': 'EUR',
    'author': 'Kiran Kantesariya',
    'email': 'risingsuntechcs@gmail.com',
    'license': 'OPL-1',
    'data': [
             'wizard/res_config.xml',
             'view/res_partner.xml',
             'view/sale_order.xml',
             'report/sale_commission_report_sun_view.xml',
             'report/report_menu.xml'
             ],
    'qweb': [],
    'css': [],
    'js': [],
    'images': [
        'static/description/main_screenshot.jpg',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
