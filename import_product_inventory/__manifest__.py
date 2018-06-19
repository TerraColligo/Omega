# -*- coding: utf-8 -*-

{'name': 'Import product in Batch',
 'version': '11.0.1.0.0',
 'category': 'other',
 'depends': ['sale_stock','purchase'],
 'author': "Nikunj Antala",
 'license': 'AGPL-3',
 'website': '',
 'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/cron.xml',
        'views/product_import_batch_view.xml',
        'wizard/import_product_wizard_view.xml',
        'wizard/export_product_view.xml',
        ],
  "qweb": [
       "static/src/xml/base.xml",
        ],
 'installable': True,
 'application': True,
 }