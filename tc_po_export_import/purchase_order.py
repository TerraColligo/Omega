from odoo import fields, models, api,_

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    external_id = fields.Char(string='External Id')
    processed = fields.Boolean(string='Processed',readonly="True",default=False)
