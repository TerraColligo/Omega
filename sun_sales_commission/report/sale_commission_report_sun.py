from odoo import tools
from odoo import fields, api,models

class sale_commission_report_ecs(models.Model):
    _name = "sale.commission.report.ecs"
    _description = "Sale Commission Report"
    _auto = False
    
    sale_agent_id = fields.Many2one("res.partner",'Sale Agent',readonly =True)
    sale_order_id = fields.Many2one("sale.order",'Order',readonly =True)
    commission = fields.Float(string='Commission',readonly =True)
    date = fields.Date(string='Date',readonly =True)
    amount_untaxed = fields.Float(string='Amount',readonly =True)
    partner_id = fields.Many2one('res.partner',string="Partner")
    
    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr,'sale_commission_report_ecs')
        self.env.cr.execute(""" CREATE or REPLACE VIEW sale_commission_report_ecs as 
            (
                select row_number() over() as id,
                    sale.id as sale_order_id,
                    sale.partner_id as partner_id,
                    sale.sale_agent_id as sale_agent_id,
                    sum(sale.amount_untaxed) as amount_untaxed,
                    sum(sale.commission_amount) as commission,
                    sale.date_order as date
                from sale_order sale join res_partner rp on rp.id=sale.partner_id 
                group by 
                    sale_order_id,
                    partner_id,
                    sale.sale_agent_id,
                    date
            )""")