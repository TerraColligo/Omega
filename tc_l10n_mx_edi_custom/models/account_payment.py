# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'


    @api.multi
    def l10n_mx_edi_is_required(self):
        self.ensure_one()
        version = self.env['account.invoice'].l10n_mx_edi_get_pac_version()
        required = (
            self.payment_type == 'inbound' and version == '3.3' and
            self.company_id.country_id == self.env.ref('base.mx') and
            self.invoice_ids.filtered(lambda i: i.type == 'out_invoice'))
        if not required:
            return required
        if not self.invoice_ids:
            raise UserError(_(
                'Is necessary assign the invoices that are paid with this '
                'payment to allow relate in the CFDI the fiscal '
                'documents that are affected with this record.'))
        # if False in self.invoice_ids.mapped('l10n_mx_edi_cfdi_uuid'):
        #     raise UserError(_(
        #         'Some of the invoices that will be paid with this record '
        #         'is not signed, and the UUID is required to indicate '
        #         'the invoices that are paid with this CFDI'))
        if not self.invoice_ids.filtered(
                lambda i: i.date_due != i.date_invoice):
            return False
        return required

