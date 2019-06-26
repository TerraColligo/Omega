from odoo import fields,models,api,_
from odoo.exceptions import ValidationError

class res_partner(models.Model):
    _inherit='res.partner'
    
    is_sale_agent = fields.Boolean(string='Sales Agent',default=False)
    commission_per = fields.Float(string='Commission in Percentage')
    sale_agent_id = fields.Many2one('res.partner',string='Sales Agent')    
    
    @api.one
    @api.constrains('commission_per')
    def _check_comm_per_value(self):
        if self.commission_per < 0.0 or self.commission_per > 100.0:
            raise ValidationError(_('Commission Percentage value must be between 0 to 100.'))