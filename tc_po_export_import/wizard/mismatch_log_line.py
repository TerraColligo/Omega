from odoo import models,fields

class import_order_transaction_log_line(models.Model):
    _name='import.orders.mismatch.log.line'
    _description = "Mismatch Log Line"
    
    message=fields.Text(string='Message')
    job_id=fields.Many2one('import.orders.mismatch.log',string='Log')