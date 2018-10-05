# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class res_partner(models.Model):
    _inherit = 'res.partner'

    sale_repr_id = fields.Many2one('res.partner', string="Sales Representative")
    comm_per = fields.Float(string="Percentage")

    @api.one
    @api.constrains('comm_per')
    def _check_comm_per_value(self):
        if self.comm_per < 0.0 or self.comm_per > 100.0:
            raise ValidationError(_('Commission Percentage value must be between 0 to 100.'))


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    @api.depends('amount_untaxed', 'amount_total', 'sale_repr_id', 'comm_per')
    def _get_total_commission_amount(self):
        for order in self:
            comm_amount = (order.amount_untaxed * order.comm_per) / 100
            order.commission_amount = comm_amount

    sale_repr_id = fields.Many2one('res.partner', string="Agent")
    comm_per = fields.Float(string="Percentage")
    commission_amount = fields.Monetary(string="Commission", compute="_get_total_commission_amount", store=True)

    @api.one
    @api.constrains('comm_per')
    def _check_comm_per_value(self):
        if self.comm_per < 0.0 or self.comm_per > 100.0:
            raise ValidationError(_('Commission Percentage value must be between 0 to 100.'))


    @api.onchange('partner_id')
    def onchange_get_sale_repr_id(self):
        self.sale_repr_id = False
        self.comm_per = 0.0
        if self.partner_id:
            self.sale_repr_id = self.partner_id.sale_repr_id
            self.comm_per = self.partner_id.comm_per or 0.0


