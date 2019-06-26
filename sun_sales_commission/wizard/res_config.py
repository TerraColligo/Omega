from odoo import fields,models,api

class res_config(models.TransientModel): 
    _inherit='res.config.settings'
        
    sale_commission_method = fields.Selection([('confirm_sale','Sales Confirmation'),('Invoive_gen','Validate Invoice'),('paid_inv','Paid Invoice')],default='confirm_sale',string='Sales Commission Applied On ')
    
    @api.model
    def get_values(self):
        res = super(res_config, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(                    
                    sale_commission_method = params.get_param('sale_commission_vts.sale_commission_method',default='confirm_sale')
                   )
        return res
    

    @api.multi
    def set_values(self):
        super(res_config,self).set_values()
        ir_parameter = self.env['ir.config_parameter'].sudo()        
        ir_parameter.set_param('sale_commission_vts.sale_commission_method', self.sale_commission_method)
        