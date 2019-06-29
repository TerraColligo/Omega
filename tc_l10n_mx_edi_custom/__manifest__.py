# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'CFDI warning disable',
    'version': '1.0',
    'summary': 'Disables SAT stamping warning on invoices when system has EDI for Mexico installed',
    'category': 'Account',
    'author': "Terra Colligo",
    'license': 'OPL-1',
    'depends': [
        'l10n_mx_edi',
    ],
    'data': [
        "views/l10n_mx_edi_report_invoice.xml",
    ],
    'installable': True,
    'auto_install': False,
}
