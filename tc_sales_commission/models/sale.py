from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class res_partner(models.Model):
    _inherit = 'res.partner'

    sale_repr_id = fields.Many2one('res.partner', string="Sales Representative")
    comm_per = fields.Float(string="Percentage")
    sale_commission_apply = fields.Selection([('invoiced','Invoiced'),('paid','Paid')],string='Sales Commission Apply')

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
        amount = 0.0
        total_amount = 0.0
        comm_amount = 0.0
        for order in self:
            if order.invoice_ids:
                if order.sale_commission_apply == 'invoiced':
                    invoice_ids = order.invoice_ids.filtered(lambda ai:ai.state in ('open','paid'))
                elif order.sale_commission_apply == 'paid':
                    invoice_ids = order.invoice_ids.filtered(lambda ai:ai.state=='paid')
                else:
                    invoice_ids = order.invoice_ids
                for inv in invoice_ids:
                    amount += inv.amount_untaxed
                total_amount = amount
                comm_amount = (total_amount * order.comm_per) / 100
            order.commission_amount = comm_amount

    sale_repr_id = fields.Many2one('res.partner', string="Agent")
    comm_per = fields.Float(string="Percentage",default=0.0)
    commission_amount = fields.Monetary(string="Commission", compute="_get_total_commission_amount")
    sale_commission_apply = fields.Selection([('invoiced','Invoiced'),('paid','Paid')])
    
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
            self.sale_commission_apply = self.partner_id.sale_commission_apply

    @api.onchange('sale_repr_id')
    def onchange_agent(self):
        self.comm_per = self.sale_repr_id.comm_per or 0.0
    