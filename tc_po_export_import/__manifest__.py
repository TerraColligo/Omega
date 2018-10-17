# -*- coding: utf-8 -*-
{
    'name' : 'Import/Export Purchase Order',
    'version' : '11.0',
    'summary': '',
    'sequence': 1,
    
    'description': """
        Export and Import Purchase Order using Xls File.
    """,    
    'category': 'Purchase',
    'images' : [],
    'depends' : ['purchase','l10n_mx'],
    'data': [
        'security/ir.model.access.csv',
        'data/import_order_mismatch_log_seq.xml',
        'data/account_tax_template.xml',
        'view/export_purchase_order.xml',
        'view/import_purchase_order.xml',
        'view/mismatch_log.xml',               
    ],      
    'installable': True,
    'application': False,
    'auto_install': False,
}
