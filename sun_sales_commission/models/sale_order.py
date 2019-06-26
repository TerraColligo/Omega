from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    @api.depends('state','amount_untaxed', 'amount_total', 'sale_agent_id', 'comm_per','invoice_ids','invoice_ids.state')
    def _get_total_commission_amount(self):
        for order in self:
            amount = 0.0
            total_amount = 0.0
            comm_amount = 0.0
            refund_amount = 0.0
            invoice_ids = False
            sale_commission_method = self.env['ir.config_parameter'].sudo().get_param('sale_commission_vts.sale_commission_method')
            if sale_commission_method == 'confirm_sale':
                if order.state=='sale':
                    total_amount = order.amount_untaxed
            else: 
                if order.invoice_ids:
                    if sale_commission_method == 'Invoive_gen':
                        invoice_ids = order.invoice_ids.filtered(lambda ai:ai.state in ('open','paid') and not ai.type=='out_refund')
                    elif order.sale_commission_apply == 'paid':
                        invoice_ids = order.invoice_ids.filtered(lambda ai:ai.state=='paid'  and not ai.type=='out_refund')
                    if invoice_ids:
                        for inv in invoice_ids:
                            amount += inv.amount_untaxed
                        total_amount = amount
                    invoice_ids = order.invoice_ids.filtered(lambda ai:ai.type=='out_refund')
                    if invoice_ids:
                        for inv in invoice_ids:
                            refund_amount+=inv.amount_untaxed
                        total_amount = total_amount - refund_amount
            comm_amount = (total_amount * order.comm_per) / 100
            order.commission_amount = comm_amount
        
    @api.multi
    @api.depends('amount_untaxed', 'amount_total', 'sale_agent_id', 'comm_per')
    def _get_total_potential_commission(self):
        for order in self:
            total_amount = order.amount_untaxed
            comm_amount = (total_amount * order.comm_per) / 100
            order.potential_commission_amount = comm_amount

    sale_agent_id = fields.Many2one('res.partner', string="Agent")
    comm_per = fields.Float(string="Percentage",default=0.0)
    commission_amount = fields.Monetary(string="Earned Commission",store=True, readonly=True, compute="_get_total_commission_amount")
    potential_commission_amount = fields.Monetary(string="Potential Commission",store=True, readonly=True, compute="_get_total_potential_commission")
    sale_commission_apply = fields.Selection([('order_confirm','Order Confirmation'),('invoiced','Invoiced'),('paid','Paid')])
    
    @api.one
    @api.constrains('comm_per')
    def _check_comm_per_value(self):
        if self.comm_per < 0.0 or self.comm_per > 100.0:
            raise ValidationError(_('Commission Percentage value must be between 0 to 100.'))

    @api.onchange('sale_agent_id')
    def onchange_agent(self):
        self.comm_per = self.sale_agent_id.commission_per or 0.0
    
    @api.onchange('partner_id')
    def onchange_partner(self):
        self.sale_agent_id = self.partner_id.sale_agent_id.id or False
        self.comm_per = self.sale_agent_id.commission_per or 0.0
        
        