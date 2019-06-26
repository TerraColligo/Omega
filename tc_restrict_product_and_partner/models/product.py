# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    barcode = fields.Char('Barcode', copy=False, oldname='ean13', required=True,
        help="International Article Number used for product identification.")

    @api.model
    def create(self, vals):
        if not vals.get('barcode'):
            raise UserError(_("Barcode is required for product."))
        return super(ProductProduct, self).create(vals)
