from odoo import models, fields, api
from datetime import date

class ImportOrderMismatchlog(models.Model):
    _name = "import.orders.mismatch.log"
    _description = "Mismatch Order Log"
    _order = 'id desc'
    
    name=fields.Char(string='Name')
    log_date=fields.Date(string='Log Date',default= date.today())
    message=fields.Text(string='Result')
    transaction_line_ids = fields.One2many("import.orders.mismatch.log.line", "job_id", string="Log")
    company_id = fields.Many2one('res.company', string="Company")
    type = fields.Selection(string='Type',selection=[('import', 'Import'), ('export', 'Export')],default='import')
    
    @api.model
    def create(self, vals):
        sequence = self.env.ref("tc_po_export_import.seq_import_purchase_order_mismatch_job")
        name = sequence and sequence.next_by_id() or '/'
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        if type(vals) == dict:
            vals.update({'name': name, 'company_id': company_id})
        return super(ImportOrderMismatchlog, self).create(vals)