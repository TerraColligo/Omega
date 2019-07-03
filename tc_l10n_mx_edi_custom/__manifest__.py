# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'EDI for Mexico Custom & Hide report Warning of the Electric Certification',
    'version': '11.2.30.6.2019',
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
